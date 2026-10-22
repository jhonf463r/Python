# Candidate target_scope repair — independent static review

- **Date:** 2026-10-22, America/Bogota.
- **Record type:** owner-supplied independent review + bounded public-branch readback.
- **Primary outcome:** `GOVERNED_IABV_CODEX_BRIDGE`.
- **Current active task:** `M1 — IDENTIFY_AND_USE_SUPPORTED_GOVERNANCE_OWNED_SCOPED_READ_ROUTE`.
- **Evidence status:** reviewer verdict is `OWNER_SUPPLIED_INDEPENDENT_REVIEW`; branch and commit metadata below were independently read back from GitHub in this session.

## Candidate identity and remote state

- Branch: `fix/iabv-operational-block-target-scope-repair-20261022`
- Candidate commit: `b7c3fffaec4ff3b78b1ca03ae64ead949236f504`
- Exact base / current main at comparison: `e61c5043bbdd8ea536ed5c9e642d80ff228ee897`
- Compare result: `ahead_by=1`, `behind_by=0`, status `ahead`.
- Changed paths only:
  - `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`, blob `1d3861dedd2734ca74e51d06647aa888d54ceed4`.
  - `IABV_v1.5/tests/test_mcp_server.py`, blob `943e05657a2b193d26806a5176a93957249b2d7f`.

## Independent review received

The Owner supplied the Sonnet 4.6 report, whose verdict is `PASS` for a static review of the supplied fragment.

- **F-TS-1 closed at source level:** the open `block_target.startswith("consult_")` exception is absent from the candidate. The gate uses an explicit `known_target_scopes` set.
- **Discriminating case A:** registered `consult_codex`, not applicable to audit, is skipped for that route.
- **Discriminating case B:** unregistered `consult_unmapped_scope` remains fail-closed and produces `operational_block_active`.
- The supplied review reports no bypass across five examined adversarial scenarios: global `*`, crossed `assistant_kind`, double `*`, registered target in a different role, and the unregistered consult-prefixed target.
- The coordinator read back the candidate source and test file; the open prefix check was absent, the finite set was present, and all eight focused test functions were present (six prior acceptance cases plus two differentiating consult-scope cases).

## Test and runtime status

- `STATIC_REVIEW=PASS` for the supplied fragment only.
- `TESTS=NOT_RUN`; this record does not claim the tests pass.
- `LIVE_SERVER_IDENTITY=UNVERIFIED`; no evidence here proves that the live MCP server runs this source revision.
- `LOCAL_SOURCE_READ=NOT_RUN`; no local checkout was read.
- `RUNTIME=NOT_RUN`; no IABV, MCP server, Codex CLI/App Server, or Ollama process was launched.
- The eight focused test bodies use a fake world-model service and call the governance-route helper. Static inspection found no direct Ollama/server-start invocation in those test bodies, but no execution or complete transitive-import side-effect validation occurred.

## Decision and guardrails

This review removes the identified static objection to the **remote candidate**. It does not close M1, identify the supported governance-owned route, authorize block release, validate the live server, merge/deploy/adopt the candidate, or authorize test execution.

```
GOVERNANCE=KEEP_BLOCKED
IMPLEMENTATION=NOT_AUTHORIZED
CANDIDATE_MERGED=NO
TESTS=NOT_RUN
LOCAL_SOURCE_READ=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
REAL_TRANSPORT=NOT_RUN
LOCAL_WORKTREE=UNTOUCHED
```

**Current route remains:** identify the actual supported governance-owned scoped-read interface/operator for the live MCP server and checkout. The candidate-specific focused tests are a separate gated follow-up and must not be run without the applicable explicit authorization in an isolated environment.
