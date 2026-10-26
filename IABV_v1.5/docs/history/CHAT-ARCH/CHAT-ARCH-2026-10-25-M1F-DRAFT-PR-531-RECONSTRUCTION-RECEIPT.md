# M1F candidate reconstruction and draft PR #531 — evidence receipt

- **Receipt ID:** `IABV_M1F_DRAFT_PR_531_RECONSTRUCTION_RECEIPT_2026-10-25`
- **Prepared at:** `2026-10-25T19:57:38-05:00` (`America/Bogota`), using the then-current observation time.
- **Source repository:** `jhonf463r/Python`
- **Main base for candidate:** `e6c3fc499a121872926c36584b91ffd22dca288f`
- **Candidate commit:** `e3618526fd20fb2a59fd30b250c68dee4c78c8c0`
- **Candidate branch:** `codex/iabv-m1f-authz-candidate-review-20261025`
- **Candidate PR:** [#531](https://github.com/jhonf463r/Python/pull/531), open draft, not merged.
- **Canonical route writeback:** [documentation PR #532](https://github.com/jhonf463r/Python/pull/532), which updates the five required front doors and adds this receipt; no product source files are changed by #532.
- **Scope:** reconstruct the already-existing M1F consolidated source candidate on live `main`, then leave the source changes reviewable without promoting them to production.

## 1. Direct verification performed in this session

### Live repository state

The GitHub commit API returned `e6c3fc499a121872926c36584b91ffd22dca288f` for `main` before the candidate branch was created. PR #530 is closed and merged to that SHA; its title and patch are documentation reconciliation, not source-code integration. GitHub fetched the #531 PR back with:

- `state=OPEN`, `draft=true`, `merged=false`, `mergeable=true` (observed on fetch-back).
- Base SHA `e6c3fc499a121872926c36584b91ffd22dca288f`; head SHA `e3618526fd20fb2a59fd30b250c68dee4c78c8c0`.
- Exactly 13 changed paths; 5,507 additions and 59 deletions.
- No status checks and no PR-triggered workflow runs were returned for this head at the time of inspection. This means no checks were reported through these queried endpoints, not that tests passed.

### Reconstruction and Git object identity

The M1F consolidated diff was read from Dropbox at `/IABV-IA-BRIDGE/OUTBOX/M1F_M1D_PLUS_M1E_CANDIDATE_VS_MAIN.diff`. Each file's unified-diff hunks were applied in memory against the exact base contents fetched from GitHub. All hunk contexts and declared line counts matched. The six existing files had base blob IDs equal to the corresponding blobs on `main`. Each reconstructed file was then submitted as a Git blob and returned exactly the target SHA declared by the diff: **13/13 target blob IDs matched**.

| File | Resulting Git blob SHA |
|---|---|
| `IABV_v1.5/src/iabv_v15/bootstrap.py` | `802f1b42881f383d9ac33fea8ee6c2c913a4da32` |
| `IABV_v1.5/src/iabv_v15/infra/mcp/server.py` | `8f74bbd7068db4d659c5c8e736e057c97152237e` |
| `IABV_v1.5/src/iabv_v15/infra/mcp/windows_handle_reader.py` | `cf3045be70e6824bdcc627ccefa14ea33faf6342` |
| `IABV_v1.5/src/iabv_v15/services/evolution/mcp_bridge_service.py` | `4278c11e2a498fc96b112a4fd5d6215cb19d977d` |
| `IABV_v1.5/src/iabv_v15/services/security/github_owner_merge_bootstrap.py` | `7d212a8334d176ac90c169a9166214dc5ae9d808` |
| `IABV_v1.5/src/iabv_v15/services/security/read_authorization.py` | `ac61ee2d82ef546ef44c59cd332cebc22f7edfd6` |
| `IABV_v1.5/src/iabv_v15/services/security/windows_crypto.py` | `052af46c43e9831583a3557167b7882ddd206d59` |
| `IABV_v1.5/tests/test_bootstrap_defer_init.py` | `b31fff13c0a7476410e626675b077cc87715023f` |
| `IABV_v1.5/tests/test_github_owner_merge_bootstrap.py` | `c8813163b74a1ebf64f3f3c98a43cd9f56fb4de8` |
| `IABV_v1.5/tests/test_mcp_bridge_service.py` | `7b4c111e56e8007989c3fada4a2beceb68982f56` |
| `IABV_v1.5/tests/test_mcp_server.py` | `62221298d3f544e93c941f6b41b23ab3b371e75f` |
| `IABV_v1.5/tests/test_read_authorization.py` | `efe42600b91f7884a7735a9abeebc6d46dfb49d1` |
| `IABV_v1.5/tests/test_windows_handle_reader.py` | `9f273f5bac57b3eed6fa3e9253b526f690b9766a` |

This validates the exact Git objects committed to the source candidate branch. It does not establish that the implementation passes tests or satisfies the full security contract. The Dropbox text-extraction result had 249,089 characters while Dropbox metadata recorded a 249,105-byte diff file. Therefore this receipt does not claim the fetched extracted text was byte-identical to the raw stored diff, or recalculate the raw diff SHA-256. Prior M1F documentation records the distinction and the normalization of a *temporary* M1E copy; originals were not overwritten.

## 2. Evidence classification

### `INDEPENDENTLY_VERIFIED`

- Live `main` base SHA and the documentation-only merge of #530.
- The base blob IDs of all six modified files match the candidate diff's declared base blob IDs.
- The 13 reconstructed target Git blob IDs match all 13 target SHAs declared in the consolidated M1F diff.
- Candidate branch commit SHA, PR #531 head/base, open draft state, changed-file count and PR contents were fetched back from GitHub.
- Exact candidate file list is the 13 paths shown in PR #531.

### `PRODUCER_REPORTED`

- M1F report says `python -m pytest IABV_v1.5/tests/test_windows_handle_reader.py -q` exited 0 with 24 passed in 0.85s.
- M1F report says AST parsing of 13 changed Python files passed and full-delta `git diff --check` exited 0.
- M1F report says the checkout was clean before reconstruction and the Git index hash was unchanged. Those are local-checkout observations reported by the producer, not direct observations of this session's environment.

### `NOT_VERIFIED`

- Raw-byte identity of the Dropbox-extracted diff in this session; native Windows APIs, actual file ACLs, root-provider identity, authentic Owner/issuer identity, authenticated IPC, production G2/G3 providers, anti-rollback persistence, real MCP transport, live protected reads and whole-organ acceptance.
- The earlier report says a prior bootstrap invocation *may* have reached `_auto_load_secrets()` before a stub was installed; whether a local secret file was read is unverified. This session did not inspect secrets or repeat that invocation.
- A container clone attempt failed with `fatal: unable to access 'https://github.com/jhonf463r/Python.git/': Could not resolve host: github.com`. Therefore tests/build/local static checks were not executed in the container. GitHub connector reads and object creation were used instead; no local Windows execution is claimed.

## 3. Canonical eight-gate acceptance matrix

The following eight gates are the IDs defined by `CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md` (blob `1322fdfb26770bcf5bdfab9fd85a7ffcee5d9f37`). All remain open for implementation acceptance. The source PR is a candidate only.

| ID / requirement | Previous/current evidence | Verification | Result | Minimum closure evidence / principal risk |
|---|---|---|---|---|
| **G1 — Authenticated Owner/governance principal and trust anchor** | Candidate has GitHub merged-PR/manifest verification code and typed trust contracts; there is no production trusted-root provisioning, authenticated local principal binding, production issuer or Owner mandate provider in AppBootstrap. `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`. | Candidate source identity verified; behavior/authority not verified. | **OPEN — NOT_ESTABLISHED** | Obtain independently verifiable trust-root material, chain, real Owner/governance principal and role/instance binding, with provenance and revocation. Without it, signatures under an untrusted supplied key cannot prove authority. |
| **G2 — Authorized catalogue publisher, producer-class policy, integrity and revocation** | Policy contracts and signature validation exist in candidate, but no trusted production catalogue/publisher, producer allowlist or authoritative revocation source is wired. | Source candidate only; no production provider verification. | **OPEN — NOT_ESTABLISHED** | Attested, versioned catalogue tied to G1, authenticated publisher/class policy, integrity check and current authoritative revocation responses. Otherwise stale or attacker-supplied policy can be trusted incorrectly. |
| **G3 — Versioned server-side operation-to-target resolver** | Candidate introduces handle-bound `OpenedTargetCapability` and checks that the resolver returns the same object and binding; no real production resolver or approved root provider is wired into composition. | Static source inspection plus exact blob identity; tests NOT_RUN here. | **OPEN — NOT_ESTABLISHED** | Implement and verify a host-owned versioned resolver and approved root provider, with caller scope unable to override target; prove every protected call consumes the same opened object. Otherwise target substitution or unresolved scope can be mis-authorized. |
| **G4 — Typed schema/evaluator wired at every protected decision point** | Candidate introduces typed requests/decisions/permits and guards both file-read and directory-list tool paths; composition is deny-only when dependencies are absent. Whole call-site inventory and behavior were not executed/reviewed here. | Candidate identities verified; test/integration execution NOT_RUN. | **OPEN — PARTIALLY DEMONSTRATED** | Independent review of all protected call sites plus negative integration tests proving missing/invalid context, permit, target binding or coordinator can never reach a read helper. Otherwise an unguarded entry point could bypass the organ. |
| **G5 — Deterministic all-block aggregation and independent per-block release** | This remains a normative requirement in v1.0.1. M1F does not provide evidence for an attested complete active set or independent per-block release workflow. | Not demonstrated by the M1F candidate PR or this session. | **OPEN — NOT_ESTABLISHED** | Verify complete active-set attestation, order-independent aggregation of all block decisions/reasons, and separately authenticated current releases per block. Otherwise a missing/omitted block could be treated as cleared. |
| **G6 — Entry 274 approval, reader, containment, budgets and audit integration** | Candidate includes handle-relative reader, same-object permit checks, bounds and local cleanup; real owner approval, production ledger/budget, native containment/ACL, and durable operation audit integration are not established. | Static/candidate-only; actual reader/runtime/Windows tests NOT_RUN. | **OPEN — PARTIALLY DEMONSTRATED** | Map each Entry 274 stage to a real live call site and produce correlated freshness, revocation, budget/ledger and audit receipts; validate native handle containment on Windows. Otherwise a source-level guard may not enforce the complete operational contract. |
| **G7 — Separately authorized conformance testing** | Producer reported 24 focused synthetic-handle tests passing. This session ran no tests because the repository was unavailable by direct clone and the bootstrap/secrets-loading path must be preflighted before test commands. | Producer-reported only; current-session execution NOT_RUN. | **OPEN — NOT_ESTABLISHED** | Under an approved isolated runner, inspect all test imports/fixtures first, then run focused unit, denial, composition and integration suites with exact commit/command/results. Native Windows tests require an appropriate Windows environment. |
| **G8 — Independent acceptance bound to exact revision and honest claim scope** | Candidate file identities and source PR were independently fetched back; full-organ static review, test receipts and external-platform evidence are incomplete. | Blob reconstruction independently verified; acceptance not performed. | **OPEN — PARTIALLY DEMONSTRATED** | Independent adversarial review and reproducible test evidence bound to exact branch/head, then fetch back checks/results. Do not infer security from hashes, source existence or a draft PR. |

```text
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
G4=OPEN_PARTIALLY_DEMONSTRATED
G5=NOT_ESTABLISHED
G6=OPEN_PARTIALLY_DEMONSTRATED
G7=NOT_ESTABLISHED
G8=OPEN_PARTIALLY_DEMONSTRATED
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
```

## 4. Test and acceptance inventory

| Test group | Result in this session | Provenance / limitation |
|---|---|---|
| Syntax / AST | `NOT_RUN` | 13-file AST pass is only `PRODUCER_REPORTED`. |
| `git diff --check` | `NOT_RUN` | Exit 0 is only `PRODUCER_REPORTED`. |
| Unit tests | `NOT_RUN` | The 24-test focused result is `PRODUCER_REPORTED`; no full candidate suite was executed here. |
| Denial/negative tests | `NOT_RUN` in this session | Test definitions in candidate are not evidence of test execution. |
| Composition/integration tests | `NOT_RUN` | AppBootstrap composition and actual provider behavior were not executed. |
| Native Windows handles / ACLs | `NOT_RUN` | Requires appropriate Windows environment. |
| Authenticated IPC / rollback-resistant replay | `NOT_RUN` | No real issuer process, authenticated peer or monotonic anti-rollback mechanism was provisioned. |
| Live MCP transport / protected read | `NOT_RUN` | Not attempted; protected access remains fail-closed. |
| Whole suite | `NOT_RUN` | No claim of full-suite acceptance. |

## 5. Current disposition and next bounded action

**Disposition:** preserve PR #531 as an open draft source candidate. Do not merge it as an authorization acceptance. No G1/G2/G3 gate is established, all eight canonical implementation prerequisites remain open, and protected reads remain `FAIL_CLOSED`. The bridge must remain `BRIDGE_NOT_READY`.

**Next action:** perform an independent whole-candidate static review of the exact #531 head and preflight the focused test/import path to prove it cannot enter the reported `_auto_load_secrets()` route before executing synthetic-only tests in an approved isolated environment. Review composition-level denial behavior and record any source-correctable defect in a separate bounded patch. Do not fabricate root, issuer, policy or workspace authority to make tests pass.