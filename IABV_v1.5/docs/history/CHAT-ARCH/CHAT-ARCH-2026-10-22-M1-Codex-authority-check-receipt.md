# M1 — Codex authority-check receipt and reconciliation (2026-10-22)

## Result

`BLOCKED_AUTHORITY_SCOPE_MODEL_UNAVAILABLE`.

Codex supplied a receipt for the reported isolated candidate and a bounded inspection. Its conclusion is consistent with the source-level adjudication: no authoritative, explicitly versioned operational-block scope model or trusted target resolver was demonstrated. Do not repair F-01–F-03 by inventing an allowlist, combination semantics, or production operation labels. Keep read/list denial and stop this repair task.

## Candidate receipt — OWNER_REPORTED

Codex reports:
- Root: `C:\temp\IABV_M1_GOVERNED_READ_CANDIDATE_20261022`
- Branch: `codex/m1-governed-scoped-read-route-20261022`
- HEAD: `cb2f2b02ade297660431e7bbd5d0dce75d10e39c`
- `git status --short`: two modified files, `server.py` and `test_mcp_server.py`; the worktree is dirty.
- No candidate files were changed during this bounded check.
- No tests, builds, scripts, runtime or transport were run.

These local observations are recorded as `OWNER_REPORTED`; the coordinator has not independently opened the Windows directory. The receipt does not authenticate a live MCP process or checkout.

## Evidence and reconciliation

### Source findings reported from the candidate — OWNER_REPORTED

- `domain/models.py`: `OperationalBlockRecord` has `target_scope` and `assistant_kind` as strings and does not itself provide a typed/versioned scope-authority contract.
- `world_model_service.py::_block_records()`: scope values are generated as strings from literals and upstream signals/fields; no shared authoritative target resolver is shown.
- `server.py::_governance_block_for_route()`: the candidate locally combines the two dimensions and contains a coded known-scope list, but this is implementation-local policy, not proof of an authoritative versioned model or trusted target resolution.

### Independently retrieved public-source facts — HEAD_SOURCE

At the reported base `cb2f2b02ade297660431e7bbd5d0dce75d10e39c`, the relevant public blobs are:
- `IABV_v1.5/src/iabv_v15/domain/models.py`: `a9033d21052c519e09f482097599c704a62ea916`
- `IABV_v1.5/src/iabv_v15/services/evolution/world_model_service.py`: `ba0b5f5d6233330b549e09863975c77c0db735d6`
- `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`: `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`

The model has no versioned registry/resolver. The WorldModel producer emits examples such as `consult_external`, `heavy_local_model`, `ui_focus_interaction`, derives some targets from `required_for[0]`, and creates `consult_<assistant_kind>` values. Registered `read_repo_file` and `list_repo_directory` call the route gate with `assistant_kind="audit"`; they do not pass the candidate-added `operation_scope` parameter. These observations support F-01 and F-02 but do not establish runtime behavior.

### Entry 274 availability — candidate-local versus public GitHub

Codex reports that Entry 274 is absent from the sparse candidate's tracked paths. That report is not contradicted by the coordinator's separate retrieval: the canonical document is available on public GitHub main at [Entry 274](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md). Thus, Entry 274 was not available in the reported candidate filesystem, but its public GitHub version was accessible to this coordinator. Do not claim Codex read the document.

Entry 274's relevant rule is explicit: use an authoritative, versioned set of supported dimensions and defined combination semantics; unknown, malformed, unsupported, partially evaluable or conflicting metadata fails closed; non-applicability must be proven against trusted identity and the authoritative model. A test matrix or locally coded known-scope list cannot create that authority.

## F-01–F-03 disposition

- **F-01 — BLOCKED:** no existing authoritative/versioned scope model or trusted target resolver was evidenced.
- **F-02 — UNRESOLVED / NOT SAFELY REPAIRABLE:** no authoritative operation-to-target map establishes which production call sites may pass `operation_scope`.
- **F-03 — UNRESOLVED / MUST FAIL CLOSED:** without the authority, a mismatching `assistant_kind` cannot prove that an unknown, malformed or conflicting `target_scope` is irrelevant.

## Stop condition and next dependency

The current bounded task is terminally blocked with `BLOCKED_AUTHORITY_SCOPE_MODEL_UNAVAILABLE`. No further source-code repair is authorized under this handoff. The next valid input must be either (a) an independently established existing authoritative/versioned scope model and target resolver, or (b) a separate explicit Owner/governance decision to commission the creation and review of such a model. Option (b) is a new design/policy task, not permission to silently invent policy in this patch.

No code files were modified by the coordinator, and no candidate code was published, committed, pushed, opened as a PR, merged or deployed. No tests/builds/runtime/transport were performed. The Owner's dirty checkout, `data/`, SQLite, secrets and `.env` were not accessed.

```text
ACTIVE_TASK=M1_IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
M1_STATUS=BLOCKED_AUTHORITY_SCOPE_MODEL_UNAVAILABLE
CODEX_RECEIPT=OWNER_REPORTED
CANDIDATE_ROOT_AND_BRANCH=OWNER_REPORTED
CANDIDATE_HEAD=cb2f2b02ade297660431e7bbd5d0dce75d10e39c
CANDIDATE_STATUS=TWO_MODIFIED_FILES_REPORTED
ENTRY_274=PUBLIC_GITHUB_SOURCE_VERIFIED; ABSENT_FROM_CANDIDATE_REPORTED
F01=BLOCKED_AUTHORITY_MISSING
F02=NO_AUTHORITY_FOR_OPERATION_SCOPE_WIRING
F03=FAIL_CLOSED_UNRESOLVED_SCOPE_COMBINATIONS
SCOPED_READ_REQUEST_APPROVAL_FLOW=NOT_IMPLEMENTED
TESTS=NOT_RUN
LIVE_MCP_IDENTITY=UNVERIFIED
LIVE_CHECKOUT_IDENTITY=UNVERIFIED
GOVERNANCE=KEEP_BLOCKED
CANDIDATE_MERGED=NO
BRIDGE=BRIDGE_NOT_READY
```
