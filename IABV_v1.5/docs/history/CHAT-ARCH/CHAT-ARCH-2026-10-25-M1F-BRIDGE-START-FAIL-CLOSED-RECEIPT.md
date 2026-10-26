# M1F follow-on — fail-closed bridge-start dependency gate

- **Receipt ID:** `IABV_M1F_BRIDGE_START_GUARD_RECEIPT_2026-10-25`
- **Observed at:** `2026-10-25T20:15:19-05:00` (`America/Bogota`).
- **Live main:** `6b732fe350b7c8db95358239efe5d53288ef32f7`.
- **Source candidate:** [PR #531](https://github.com/jhonf463r/Python/pull/531), open draft; not merged.
- **Candidate branch:** `codex/iabv-m1f-authz-candidate-review-20261025`.
- **Candidate commit:** `0d1a9ff1639aabb7134d39888339ba12cc382b5c`.
- **Parent:** `e3618526fd20fb2a59fd30b250c68dee4c78c8c0`.
- **Scope:** correct the source-level lifecycle path that could start MCP/tunnel transport while the read-authorization coordinator was missing or unconfigured. No runtime or authority state was changed.

## 1. Source change

### `IABV_v1.5/src/iabv_v15/services/evolution/mcp_bridge_service.py`

- Previous candidate blob: `4278c11e2a498fc96b112a4fd5d6215cb19d977d`.
- New candidate blob: `5c573dc9a7288d8b952cbf5c3002f3746d78356a`.
- `_start_locked()` now runs `_authorization_organ_gate_block()` before the operational World Model gate and before either the MCP server runner or Cloudflared tunnel runner starts.
- The preflight fails closed when the imported coordinator type is unavailable, the injected object is not exactly `ReadAuthorizationCoordinator`, the coordinator cannot report missing requirements safely, or the coordinator reports any required dependency absent.
- Denial is surfaced through the existing blocked/failed status fields. This does not create or provision a trust root, Owner mandate, policy, resolver, IPC, replay provider or approved workspace root.

### `IABV_v1.5/tests/test_mcp_bridge_service.py`

- Previous candidate blob: `7b4c111e56e8007989c3fada4a2beceb68982f56`.
- New candidate blob: `1ef26acd54a9ccf1caab0f6a1ac2294b2989e570`.
- Added `test_bridge_stays_stopped_without_read_authorization_coordinator`.
- Added `test_bridge_stays_stopped_when_authorization_coordinator_is_unconfigured`.
- The existing bridge lifecycle test fixture now injects a synthetic coordinator whose dependencies are non-null solely to exercise unrelated lifecycle success paths. This fixture does not invoke authorization decisions and is not evidence of production provider authenticity or positive protected reads.

## 2. Reconstruction provenance

The prior M1F reconstruction at commit `e3618526fd20fb2a59fd30b250c68dee4c78c8c0` independently matched all 13 target Git blob IDs declared by the consolidated M1F diff. After the bridge-start correction, the source branch was fetched back:
- 11 remaining files still matched their exact original M1F target blob IDs.
- The two amended files were fetched and their new blob IDs matched `5c573dc9a7288d8b952cbf5c3002f3746d78356a` and `1ef26acd54a9ccf1caab0f6a1ac2294b2989e570`.
- PR #531 was fetched back as open, draft and not merged; head `0d1a9ff1639aabb7134d39888339ba12cc382b5c`; 13 changed paths; 5,593 additions and 60 deletions.
- GitHub returned no status checks for the inspected commit and no PR workflow runs.

## 3. Verification classification

### `INDEPENDENTLY_VERIFIED`
- Live `main` tip `6b732fe350b7c8db95358239efe5d53288ef32f7`.
- Candidate branch head, PR #531 status, base/head metadata and changed-file list fetched back.
- New bridge source/test blob identities fetched back exactly.
- 11 remaining files still match the original M1F target Git blob IDs.
- Source diff behavior reviewed statically: missing/unconfigured coordinator blocks startup before server/tunnel runner calls.

### `PRODUCER_REPORTED`
- Original M1F run: 24 focused `test_windows_handle_reader.py` tests passed; AST parsing for the original 13 files; `git diff --check` exit 0. None was rerun by this follow-on task.

### `NOT_VERIFIED` / `NOT_RUN`
- The two new bridge tests, all other unit tests, syntax/AST commands, `git diff --check`, build, app composition/runtime, real MCP transport and protected reads were not executed in this session.
- A local clone attempt failed with `Could not resolve host: github.com`. GitHub connector access was sufficient to fetch/commit blobs, but it is not a local test runner.
- The shared test module, its direct imports and `conftest.py` were inspected as a limited secret-autoload preflight. The target test does not directly import `AppBootstrap` or invoke `_auto_load_secrets()`; the full transitive import path has not been executed. No secret was read.
- Native Windows `NtCreateFile`, `CloseHandle`, actual ACLs, authenticated IPC peer identity, rollback-resistant replay and Owner/workspace-root trust assets remain unverified. This session did not access the Owner's local Windows session.
- The new gate verifies dependency presence only. It does not prove provider authenticity or serve as a formal acceptance token for all eight gates. It must not be described as bridge acceptance.

## 4. Canonical disposition

```text
TASK=M1F_BRIDGE_START_FAIL_CLOSED_DEPENDENCY_GUARD
SOURCE_RESULT=PATCHED_IN_DRAFT_CANDIDATE; FETCHBACK_VERIFIED
CANDIDATE_HEAD=0d1a9ff1639aabb7134d39888339ba12cc382b5c
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_SOURCE_MERGE=NOT_PERFORMED
NEXT_ACTION=RUN_FOCUSED_TESTS_IN_APPROVED_ISOLATED_RUNNER; CONTINUE_REVIEW; PRESERVE_FAIL_CLOSED
```

The existing full canonical acceptance matrix and original M1F reconstruction receipt remain authoritative evidence for the eight gate definitions. This receipt records a source-candidate correction only.
