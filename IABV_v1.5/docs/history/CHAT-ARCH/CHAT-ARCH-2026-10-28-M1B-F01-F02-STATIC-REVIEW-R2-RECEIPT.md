# M1B PR #555 — Independent static review of F-01/F-02 correction (R2)

**TASK_ID:** `M1B_PR555_F01_F02_FIX_DELTA_INDEPENDENT_STATIC_REVIEW_R2_20261028`
**Reviewer:** Claude / Sonnet 5, as reported in the Owner-supplied review.
**Mode:** read-only static review and exact diff; module, pytest, build, CLI, MCP, runtime and E2E were not run by this reviewer.

## Verdict

```text
HEAD_VERIFIED=c36ee5ed177a3b5afee764c277cc4a8b243594c8
FILES_AND_HASHES=EXACT_MATCH
DELTA_SCOPE=ONLY_F01_F02
F01_DISPOSITION=CLOSED_BY_STATIC_REVIEW
F02_DISPOSITION=CLOSED_BY_STATIC_REVIEW
REGRESSIONS_FOUND=NONE_WITHIN_REVIEWED_DELTA
TESTS_RUN_BY_REVIEWER=NOT_RUN
CODEX_FOCUSED_3_PASSED=OWNER_REPORTED
CODEX_FULL_FILE_37_PASSED=OWNER_REPORTED
VERDICT=PASS
TOCTOU=PREVIOUSLY_KNOWN_RESIDUAL_LIMITATION
BRIDGE=BRIDGE_NOT_READY
```

## Revision and identity

- PR: [#555 — M1B: add fail-closed read-only context reader](https://github.com/jhonf463r/Python/pull/555).
- Prior HEAD: `6c601c99bb9cc2111f9dde2f6986aefcc0393785`.
- Reviewed HEAD: `c36ee5ed177a3b5afee764c277cc4a8b243594c8`.
- Base: `79ab8c50eaa7518120d5ebed9db4747d395a21cb`.
- Claude's receipt states that both files were fetched from the exact GitHub contents API ref and byte-verified. This ChatGPT session has independently fetched the current GitHub blobs, but did not run pytest.

| File | Git blob | SHA-256 |
|---|---|---|
| `IABV_v1.5/src/iabv_v15/infra/persistence/control_master_context_reader.py` | `6ca2bdd8a62e3748ae902da754ffd377f0724623` | `8b4a6d4d161551562587415d8cfb4a4860db6d29804c432283d039893345d19b` |
| `IABV_v1.5/tests/test_control_master_context_reader.py` | `593991a818f2be547e97d6904f3a111f64d62562` | `f2f9f53b4782c64aa1f5a8a00108c52e2b68aa25aef58439ad36040e4e679587` |

## Exact delta

Claude reports that the full diff between the two exact HEADs contains only two additions:

1. A `_reject_nonstandard_json_constant(token)` function which raises `ValueError`, and the `parse_constant=_reject_nonstandard_json_constant` argument to the existing `json.loads` call.
2. A parameterized test for `NaN`, `Infinity` and `-Infinity` in `sections[0].confidence`; the test asserts the raw token exists unquoted before writing the artifact and then asserts the precise fail-closed result.

No other lines in the two files changed in the R1-to-R2 diff, according to the reviewer’s complete `diff -u`.

## F-01 — closed by static review

Claude traced the exception path: the callback raises `ValueError`, which is caught by the pre-existing R1 parsing exception handler and returned as `Availability.UNAVAILABLE`, `reason="ARTIFACT_INVALID_OR_UNREADABLE"`, and `content=None`. Rejection happens during parsing before schema validation could accept `float('nan')`.

The reviewer reports an isolated reproduction of the exact `parse_constant` mechanism: all three non-standard tokens raise `ValueError`, while ordinary numeric and timestamp values remain unaffected. The two real `main` artifacts inspected in that review contained zero occurrences of the three tokens. This was a mechanism-level reproduction, not execution of the complete module.

## F-02 — closed by static review

The test constructs an otherwise valid portable-context package, substitutes each unquoted token into the serialized `confidence` field, verifies the raw byte-stream contains that unquoted token, and then asserts `UNAVAILABLE`, `ARTIFACT_INVALID_OR_UNREADABLE`, and `content is None`.

## Regressions and residuals

- No regression was identified within the exact two-file delta. The reviewer reports that schema validators, route logic, freshness, duplicate-key handling, UTF-8 handling, and the prior CRLF region are unchanged.
- The `resolve()` to `open()` filesystem TOCTOU limitation remains the residual recorded in R1; this correction does not address it.
- The original 38 CRLF lines remain unchanged. Whether the 23 new test lines themselves use CRLF or LF was not inspected by Claude and remains `UNKNOWN` in this receipt.
- Other repository consumers of non-standard JSON constants were not searched; that broader question remains `UNKNOWN` and is outside this bounded review.

## Test-evidence boundary

Codex reported Python 3.13.2 / pytest 9.0.3 and the following results in an API-backed minimal harness:

- Focused test: `3 passed, 34 deselected`, exit code 0.
- Entire reader test file: `37 passed`, exit code 0.

These remain `OWNER_REPORTED`. Claude ran no tests; this ChatGPT session also did not run pytest. The harness did not load repository-level pytest configuration, so the results are scoped to the exact two files in that harness, not a full-repository or integration run.

## Governance boundary

```text
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_CANDIDATE_MERGE=NOT_AUTHORIZED
C:\Python=DO_NOT_TOUCH
```

This receipt preserves the reviewer-supplied report and evidence labels. It does not approve or merge PR #555, establish authority, or claim runtime readiness.