# M1A / PR #549 — isolated test execution receipt for 519c55a5

- Date: 2026-10-27 (America/Bogota).
- Repository: `jhonf463r/Python`.
- PR: https://github.com/jhonf463r/Python/pull/549.
- Branch: `codex/m1a-g1-mcp130-entra-implementation-20261027`.
- Tested candidate SHA reported: `519c55a5b96a5e0b3826b54bf92726ef7f1b9c28`.
- Parent candidate: `b55a39322d04eff5fc501629c5f331d8ea22c291`.
- Original PR base SHA: `a8624c30744da7f593d6a1c829e48aa229c8efca`.
- `main` before this documentation-only update: `7780db1b33304923c17a0247403cb789c7907e01`.
- Evidence distinction: execution counts and local log filenames below are owner-provided from Codex; this documentation writer could not inspect the local `%TEMP%` logs. The commit identity, parent and test-only diff were independently fetched from GitHub.

## Candidate commit verification

GitHub confirms commit [`519c55a5b96a5e0b3826b54bf92726ef7f1b9c28`](https://github.com/jhonf463r/Python/commit/519c55a5b96a5e0b3826b54bf92726ef7f1b9c28), message `[skip ci] Fix MCP test fixture contracts`, parent `b55a39322d04eff5fc501629c5f331d8ea22c291`, changing only `IABV_v1.5/tests/test_mcp_server.py` (+33/-7).

Static inspection of the diff confirms these test-only adjustments:
- set Streamable HTTP test-client base URL to loopback `http://127.0.0.1:8000` so the security Host middleware accepts the test;
- construct a real synthetic `EntraTokenVerifier` and `AuthSettings` for the sealed-preflight immutability contract;
- give the fake WorldModel service its `scan_stats` field;
- parse the JSON-RPC body from the SSE `data:` frame rather than assuming direct JSON response content.

No production source or security control changed in this commit.

## Reported isolated environment and results

- Python 3.13.2 was unavailable; Codex used Python 3.14.4 inside a venv within a fresh temporary clone.
- Reported versions: `mcp==1.30.0`, `pytest==9.2.0`, plus project/dev dependencies.
- The clone was detached at the required previous candidate SHA and initially clean; the post-commit clone was reported clean at the new HEAD. `C:\Python` was not touched.
- No real Entra/JWKS calls, server start, tunnel start, protected reads, manual CI workflow or merge occurred.

First combined run:
```text
194 passed; 4 failed; exit code 1
```

After test-only corrections, reported suite results:

| Suite | Reported result | Exit |
|---|---:|---:|
| `test_entra_token_verifier.py` | 36 passed; 1 warning | 0 |
| `test_mcp_server.py` | 90 passed | 0 |
| `test_mcp_audit_tools.py` | 56 passed | 0 |
| `test_mcp_bridge_service.py` | 16 passed | 0 |
| Combined four-suite run | 198 passed; 1 warning | 0 |

The warning was reported as a short synthetic HMAC key in a negative test. It is not reported as a production key or credential.

Reported local log files:
- Initial combined run: `%TEMP%\iabv-pr549-tests-12d55747eb544495afdd53653ed34e39.log`
- Final combined run: `%TEMP%\iabv-pr549-full2-87b7105b3d524b78be099106a45daada.log`
- Verifier: `%TEMP%\iabv-pr549-test_entra_token_verifier-16fbe37a44f24283a8cf6e108b77eb6b.log`
- MCP server: `%TEMP%\iabv-pr549-test_mcp_server-9c9ee8268b564cc19f090e9dd7a432c6.log`
- Audit tools: `%TEMP%\iabv-pr549-test_mcp_audit_tools-5c5b0760ccbe43fa9a6bfdebe957ee90.log`
- Bridge service: `%TEMP%\iabv-pr549-test_mcp_bridge_service-af2b3ddb2f954dc1b3475c8dda96f12e.log`

## Honest boundary

`LOCAL_TESTS=OWNER_REPORTED_PASS`; this execution was not independently reproduced here. `PYTHON_3_13_2=NOT_AVAILABLE`; actual validation used Python 3.14.4. `GITHUB_ACTIONS_CI=NOT_RUN`; the commit message contains `[skip ci]` and no workflow was started manually. Local mock/synthetic tests do not exercise production Entra, mandate revocation, G1/G2/G3 providers or a real MCP bridge session.

## Preserved state

```text
PR=OPEN/DRAFT/UNMERGED
HEAD=519c55a5b96a5e0b3826b54bf92726ef7f1b9c28
TEST_SUITES=4_REPORTED_PASS
COMBINED=198_PASSED; 1_WARNING; EXIT=0
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
MERGE=NOT_AUTHORIZED
PRODUCTION_ACTIVATION=NOT_AUTHORIZED
INDEPENDENT_REVIEW_OF_519C=PENDING
```

Next action: bounded static review of the exact current HEAD `519c55a5b96a5e0b3826b54bf92726ef7f1b9c28`; then focus on the concrete missing authority/revocation producers rather than repeating these tests. Do not merge, configure Entra, enable operations or activate the bridge until the separate authority gates are actually satisfied.

## Addendum — static delta review completed and process-learning protocol updated (2026-10-27)

The exact test-only delta at 519c55a5b96a5e0b3826b54bf92726ef7f1b9c28 has subsequently received a bounded static review in [CHAT-ARCH-2026-10-27-M1A-PR549-519C-STATIC-DELTA-REVIEW.md](./CHAT-ARCH-2026-10-27-M1A-PR549-519C-STATIC-DELTA-REVIEW.md). The earlier pending indicator above is historical and is superseded by this addendum.

```text
EXACT_DELTA_REVIEW=COMPLETED
NEW_P0=0
NEW_P1=0
NEW_CONFIRMED_P2=0
REVIEW_SCOPE=TESTS_TEST_MCP_SERVER_PY_ONLY
LOCAL_TESTS=OWNER_CODEX_REPORTED_PASS; 198_PASSED; 1_WARNING; EXIT=0
LOCAL_LOGS=NOT_INDEPENDENTLY_RETRIEVED_IN_THIS_SESSION
PYTHON_3_13_2=NOT_AVAILABLE_IN_REPORTED_RUN
GITHUB_ACTIONS_CI=NOT_RUN
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
MERGE=NOT_AUTHORIZED
PRODUCTION_ACTIVATION=NOT_AUTHORIZED
```

Method-level learning is versioned in [UAAL-CFCP-001](./CHAT-ARCH-2026-10-27-UAAL-EVIDENCE-TO-CAUSAL-FRONTIER-CONTINUITY-PROTOCOL-v1.md). This is a persistent documented protocol update, not a claim that ChatGPT, Codex and IABV automatically share a runtime or autonomous memory.

Next frontier: bounded, read-only inspection of the concrete G1 provider chain in the live PR #531 candidate, with no broad re-inventory, no fabricated authority and no merge/rebase.
