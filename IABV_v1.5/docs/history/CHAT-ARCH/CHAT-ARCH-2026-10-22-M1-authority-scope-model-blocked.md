# M1 — Authoritative scope-model check blocked (2026-10-22)

## Decision

`BLOCKED_AUTHORITY_SCOPE_MODEL_UNAVAILABLE`

The bounded, source-backed check found no authoritative, versioned operational-block scope registry/resolver or complete trusted operation-to-target mapping in the permitted source set. Do not repair F-01–F-03 by inventing an allowlist, dimension-combination semantics, or operation labels. Keep reads denied and stop this repair attempt.

## Evidence inspected

This check used only the specified source paths at the Owner-reported candidate base `cb2f2b02ade297660431e7bbd5d0dce75d10e39c`, plus canonical Entry 274:

- `IABV_v1.5/src/iabv_v15/domain/models.py`, blob `a9033d21052c519e09f482097599c704a62ea916`: `OperationalBlockRecord` contains `target_scope: str` and `assistant_kind: str`. The model provides neither a finite/versioned scope vocabulary nor an authoritative evaluator/resolver.
- `IABV_v1.5/src/iabv_v15/services/evolution/world_model_service.py`, blob `ba0b5f5d6233330b549e09863975c77c0db735d6`, `_block_records`: examples are emitted as literals such as `consult_external`, `heavy_local_model` and `ui_focus_interaction`; other values are copied from `gate.required_for[0]` or generated as `consult_{tool.assistant_kind}`. These are producers/examples, not a versioned authority or a complete operation-target map.
- `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`, blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`: `_governance_block_for_route` evaluates `assistant_kind` without evaluating `target_scope`. Registered `read_repo_file` and `list_repo_directory` invoke the gate with `assistant_kind="audit"` and do not pass `operation_scope`.
- [Entry 274 — consolidated read-decision contract](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md): requires an authoritative, versioned set of supported scope dimensions and explicit combination semantics. Unknown, malformed, unsupported, partially evaluable or conflicting metadata must fail closed; non-applicability must be proven by the authoritative model. The contract explicitly forbids inventing production scope dimensions from a test matrix.

## F-01–F-03 disposition

- **F-01 — BLOCKED:** no authoritative/versioned model or trusted target resolver was found in the permitted evidence.
- **F-02 — NOT REPAIRABLE SAFELY YET:** no source-backed operation-to-target mapping exists from which to wire `operation_scope` at registered tool call sites.
- **F-03 — NOT REPAIRABLE SAFELY YET:** without the authority above, the gate cannot reliably distinguish a validated mismatch from unknown, malformed or conflicting metadata. Do not treat a mismatching `assistant_kind` as proof that `target_scope` is irrelevant.

## Provenance and limits

The source blobs above are directly retrievable from GitHub at the stated base. The Owner supplied the complete diff and reported the isolated candidate path as `C:\temp\IABV_M1_GOVERNED_READ_CANDIDATE_20261022`, branch `codex/m1-governed-scoped-read-route-20261022`, base/HEAD `cb2f2b02ade297660431e7bbd5d0dce75d10e39c`; those local candidate identity/details remain `OWNER_REPORTED`. This ChatGPT coordinator session has no filesystem or dispatch action for the Owner's Windows Codex session, so it did not independently open that directory. No claim is made that the candidate's local state or live server was inspected.

No candidate files were changed by this check. No tests, builds, lint, scripts, runtime, processes, MCP calls, transport, local checkout, `data/`, SQLite, secrets or `.env` were accessed. No code commit, push, PR, merge or deployment was made.

```text
ACTIVE_TASK=M1_IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE
M1_STATUS=BLOCKED_AUTHORITY_SCOPE_MODEL_UNAVAILABLE
AUTHORITY_SCOPE_MODEL=NOT_FOUND_IN_PERMITTED_PINNED_SOURCE_SET
F01=BLOCKED
F02=NOT_WIRED_NO_AUTHORIZED_MAPPING
F03=FAIL_CLOSED_NO_AUTHORITY_TO_PROVE_MISMATCH
CANDIDATE_LOCAL_IDENTITY=OWNER_REPORTED
CANDIDATE_DIRECT_FILESYSTEM_INSPECTION=NOT_PERFORMED_BY_CHATGPT_COORDINATOR
TESTS=NOT_RUN
LIVE_MCP_IDENTITY=UNVERIFIED
LIVE_CHECKOUT_IDENTITY=UNVERIFIED
GOVERNANCE=KEEP_BLOCKED
CANDIDATE_MERGED=NO
BRIDGE=BRIDGE_NOT_READY
```

## Required stop behavior

Stop this repair attempt. Do not add mappings, enum values, a registry, a resolver, guessed call-site scopes, or tests intended to validate an invented policy. The read/list path remains closed. A future continuation requires an independently established authoritative/versioned scope model or an explicit Owner/governance decision to create and review such a model; that would be a separate task, not a repair inferred from this diff.
