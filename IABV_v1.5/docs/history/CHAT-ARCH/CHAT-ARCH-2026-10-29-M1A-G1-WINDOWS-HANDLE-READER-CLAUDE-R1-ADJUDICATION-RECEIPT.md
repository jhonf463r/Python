# M1A G1 — Windows handle-reader static-review adjudication receipt

- **TASK_ID:** `M1A_G1_REMAINING_WINDOWS_SECURITY_SURFACE_STATIC_REVIEW_R1_20261029`
- **Adjudication date:** 2026-10-29 (America/Bogota)
- **Status:** `CLAUDE_STATIC_REVIEW_RECEIVED; TARGETED_SOURCE_FINDINGS_REBOUND; CODE_FIX_NOT_RUN`
- **Scope:** documentary adjudication only on the existing candidate; no code edits, tests, build, native Windows execution, MCP/runtime, credentials, enrollment, protected reads, tunnel or merge performed by this adjudication.

## 1. Objective and live revision

**`VERIFIED`** — Live `main` commit observed through the repository commit feed: `79ab8c50eaa7518120d5ebed9db4747d395a21cb`. The canonical `CURRENT-STATE.md` contents endpoint returned an empty transport body, but its reported blob `5945b23fdb5c13ce1068ca5d2d9e6513a1a06b95` was fetched directly and contains 1,068,486 characters. The canonical opening still incorrectly describes M1B as local/unpublished; this conflict remains a proposal/main-adoption issue and is not silently corrected here.

**`VERIFIED`** — PR [#556](https://github.com/jhonf463r/Python/pull/556) is open, draft, unmerged, base `79ab8c50eaa7518120d5ebed9db4747d395a21cb`, HEAD `e1b430956146c4aa0cadc1df2c3df92150b7f7ea`, 33 changed files. This is exactly the HEAD named by Claude's assignment. PR [#557](https://github.com/jhonf463r/Python/pull/557) remains a separate open, draft, unmerged documentation proposal.

## 2. Exact artifact identity

Claude reports that all seven expected Git blob IDs and SHA-256 values matched. This session independently fetched all seven files at the exact PR #556 HEAD and verified the returned **Git blob IDs** against the assignment; the connector did not independently recalculate the seven SHA-256 values.

| Artifact | Git blob SHA — independently fetched |
|---|---|
| `src/iabv_v15/services/security/windows_crypto.py` | `052af46c43e9831583a3557167b7882ddd206d59` |
| `src/iabv_v15/services/security/windows_cng_key_store.py` | `25a9df82c423fba07ec5b672a3c04667c0d25cf3` |
| `src/iabv_v15/infra/mcp/windows_handle_reader.py` | `cf3045be70e6824bdcc627ccefa14ea33faf6342` |
| `tests/test_g1_owner_enrollment_candidate.py` | `2dbcaadfebccc39196bec4560122cdee235cc7cf` |
| `tests/test_windows_handle_reader.py` | `9f273f5bac57b3eed6fa3e9253b526f690b9766a` |
| `tests/test_read_authorization.py` | `e796237ae4d1743e893ceced93e07213ca2354d0` |
| `tests/test_github_owner_merge_bootstrap.py` | `c8813163b74a1ebf64f3f3c98a43cd9f56fb4de8` |

The directly relevant source files are available at [the exact reader blob](https://github.com/jhonf463r/Python/blob/e1b430956146c4aa0cadc1df2c3df92150b7f7ea/IABV_v1.5/src/iabv_v15/infra/mcp/windows_handle_reader.py), [the exact reader tests](https://github.com/jhonf463r/Python/blob/e1b430956146c4aa0cadc1df2c3df92150b7f7ea/IABV_v1.5/tests/test_windows_handle_reader.py), and [the exact server integration](https://github.com/jhonf463r/Python/blob/e1b430956146c4aa0cadc1df2c3df92150b7f7ea/IABV_v1.5/src/iabv_v15/infra/mcp/server.py).

## 3. Adjudicated findings

### F-556-01 — partial directory listing on cap overflow

**Disposition:** `STATIC_DEFECT_CONFIRMED`.

- **`VERIFIED` — exact source behavior:** `windows_handle_reader.py:625-628` appends an entry, detects `len(entries) > cap`, pops the newest entry, sets `truncated=True`, and immediately returns `{"path": ..., "entries": entries, "truncated": True}`. The normal sort is only reached at line 634, so the overflow return is also unsorted.
- **`VERIFIED` — caller propagation:** `server.py:1114-1120` returns the reader result directly and maps `WindowsHandleReaderError` to a denial payload. There is no sanitization in that call site that removes the partial list.
- **`VERIFIED` — coverage gap in the reviewed test:** `test_windows_handle_reader.py:429-461` makes the enumerator report `ERROR_NO_MORE_FILES` on its first call and asserts an empty list. It does not exercise cap+1.
- **Prior-art contract boundary:** the historical M0B consolidated contract candidate at [blob `eb8ea575ea4081fece851c3ca2c5a042e7b781b8`](https://github.com/jhonf463r/Python/blob/79ab8c50eaa7518120d5ebed9db4747d395a21cb/IABV_v1.5/docs/history/CHAT-ARCH/CHAT-ARCH-2026-10-13-278-m0b-r8-1-consolidated-contract-candidate-274-3.md) explicitly specifies whole-list denial on entry 201 and no partial names. It is prior design evidence, not a claim that the older contract was adopted as current canonical runtime policy.
- **Minimal intended correction:** on observing entry `cap+1`, discard all collected names and raise `WindowsHandleReaderError("LIST_LIMIT_EXCEEDED")` (or use the already-established equivalent fail-closed reason after verifying the local vocabulary). Never return an `entries` field from the overflow path.
- **Discriminating tests required:** cap valid entries succeeds in deterministic name order; cap+1 denies without names; small cap/three entries exercises the exact path; malformed metadata still denies. Tests must verify no partial payload reaches the caller.
- **Execution status:** `NOT_RUN`.

### F-556-02 — hard-link count has no policy check

**Disposition:** `STATIC_GAP_CONFIRMED; CONTAINMENT_IMPACT_REQUIRES_TARGETED_VALIDATION`.

- **`VERIFIED` — exact source behavior:** the identifier `NumberOfLinks` occurs only in the `_FILE_STANDARD_INFO` declaration at line 121. `_open_component` queries `_FILE_STANDARD_INFO` at line 413 and checks only `standard.Directory` at line 414; it does not read or enforce `standard.NumberOfLinks`.
- **Prior-art contract boundary:** the same historical consolidated contract candidate specifies that hard-linked objects must be denied unless containment is proven and requires a link count of one (or denial if it is unavailable). Treat this as relevant intended-security prior art, not as a claim that this old candidate is itself canonical.
- **`INFERENCE` — risk:** absent link-count handling, this reader does not locally establish the older contract's hard-link invariant. Whether a particular hard-linked object can violate the current approved-object/checkout scope must not be claimed as a demonstrated native exploit from static inspection alone.
- **Minimal intended correction:** fail closed when the opened object's link count cannot be reliably obtained or does not satisfy the reviewed containment policy. The proposed v1 policy is to deny `NumberOfLinks != 1`, with a stable denial code such as `HARD_LINK_DENIED`; review compatibility and the native Windows meaning of the field before finalizing the patch.
- **Discriminating tests required:** synthetic `NumberOfLinks == 1` may proceed; `NumberOfLinks == 2` denies before reading/listing; query failure denies; confirm the same denial applies to each opened component where the policy requires it. A synthetic test checks the Python control flow, not native Windows semantics.
- **Execution status:** `NOT_RUN`.

## 4. Other findings and untouched scope

- **F-556-03, sensitivity filter:** `UNKNOWN` in this adjudication. `windows_handle_reader.py:444-447` calls `is_sensitive_path` before lexical parsing, but the implementation of `audit_tools.is_sensitive_path` was not read here. No defect is asserted without that evidence.
- **F-556-04, key possession:** Claude reports the CNG store returns public key material and does not sign in that module. This session confirms the exact blob identity, not every semantic claim in the module. Whether `authenticated_github_enrollment.py` proves private-key possession remains `UNKNOWN`.
- **H-01/H-02:** not reopened; this review yielded no new evidence that adjudicates them.
- Remaining candidate files and unreviewed consumer bodies are `UNKNOWN`, except for the narrow server call site noted above.
- **Tests/build/runtime/native Windows:** `NOT_RUN`. Claude ran no tests. No execution evidence is inferred from source or test existence.

## 5. Updated task-local world model

- `M1A_HEAD=e1b430956146c4aa0cadc1df2c3df92150b7f7ea` — `VERIFIED`.
- `F-556-01=STATIC_DEFECT_CONFIRMED` — exact overflow branch returns partial, unsorted names.
- `F-556-02=STATIC_GAP_CONFIRMED` — link-count policy is absent; real-world containment impact is not runtime-verified.
- `PRODUCTION_PROTECTED_READ_PATH=FAIL_CLOSED` — preserved according to the current candidate's unconfigured workspace-root provider design; no protected-read path was exercised.
- `FIRST_OPEN_EDGE=REPAIR_AND_TEST_F-556-01/F-556-02`.
- `NEXT_TASK=PREPARE_BOUNDED_CODEX_REPAIR_HANDOFF`; code edits/tests are not performed by this receipt. Any execution must use the existing PR #556 candidate and requires explicit authorization for those effects; do not create another branch/PR, rebase, merge, generate keys/manifests, perform protected reads or enable runtime/tunnel.

## 6. Security invariants

```text
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_CANDIDATE_MERGE=NOT_AUTHORIZED
C:\\Python=DO_NOT_TOUCH
TESTS/BUILD/NATIVE_WINDOWS_RUNTIME=NOT_RUN
```

This is an adjudication receipt and task-local model update. It does not establish G1/G2/G3, make the PR candidate canonical, or prove later causal reuse of the Space-Time method.
