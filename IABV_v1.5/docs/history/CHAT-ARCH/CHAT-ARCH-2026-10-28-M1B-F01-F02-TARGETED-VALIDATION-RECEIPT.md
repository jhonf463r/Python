# M1B PR #555 — F-01/F-02 exact-head validation receipt

**TASK_ID:** M1B_PR555_API_HARNESS_TARGETED_TEST_AND_SUITE_R2_20261028  
**Receipt origin:** Codex on Windows, 2026-10-28, 11:19 p.m. America/Bogota  
**Status:** TESTS=OWNER_CODEX_REPORTED_PASS; the current ChatGPT session verified GitHub revision/file identities and reconciled this receipt but did not independently rerun pytest.

## 1. Exact route and provenance

- Repository: jhonf463r/Python.
- main: 79ab8c50eaa7518120d5ebed9db4747d395a21cb.
- Canonical CURRENT-STATE.md Git blob reported and corroborated by the GitHub file metadata: 5945b23fdb5c13ce1068ca5d2d9e6513a1a06b95. A normal contents read returned an empty body; Codex reports recovering the exact blob through the authenticated gh route. Empty connector output was not treated as an empty file.
- Active route recorded in the receipt: M1B_CONTEXT_READER_CANDIDATE_RECONCILIATION.
- PR #555: [M1B read-only context reader](https://github.com/jhonf463r/Python/pull/555), open/draft/unmerged at the time of reconciliation.
- Branch and refs/pull/555/head: c36ee5ed177a3b5afee764c277cc4a8b243594c8.
- Previous candidate head: 6c601c99bb9cc2111f9dde2f6986aefcc0393785.
- Parent of current head: d51007d06adc627b726c603c542dbdda030350a1.

## 2. Exact file identity

| Path | Git blob | SHA-256 |
|---|---|---|
| IABV_v1.5/src/iabv_v15/infra/persistence/control_master_context_reader.py | 6ca2bdd8a62e3748ae902da754ffd377f0724623 | 8b4a6d4d161551562587415d8cfb4a4860db6d29804c432283d039893345d19b |
| IABV_v1.5/tests/test_control_master_context_reader.py | 593991a818f2be547e97d6904f3a111f64d62562 | f2f9f53b4782c64aa1f5a8a00108c52e2b68aa25aef58439ad36040e4e679587 |

The Codex receipt states that blobs and SHA-256 matched before and after materialization. This session separately retrieved the same branch files and confirmed their Git blob identifiers and calculated SHA-256 values from the returned UTF-8 content.

## 3. Source correction and discriminating test

F-01 adds an explicit parse_constant callback to reject NaN, Infinity and -Infinity in Python's JSON parser. A ValueError enters the existing fail-closed parsing outcome: Availability.UNAVAILABLE, reason ARTIFACT_INVALID_OR_UNREADABLE, and content is None.

F-02 adds a parametrized test for all three values in sections[0].confidence.

## 4. Reported execution

Environment reported by Codex: Python 3.13.2; pytest 9.0.3. PYTHONPATH=<harness>\src; PYTHONDONTWRITEBYTECODE=1.

Focused command:

~~~powershell
python -B -m pytest -p no:cacheprovider --tb=short tests/test_control_master_context_reader.py -k test_nonstandard_json_numeric_constants_are_unavailable
~~~

Reported result: **3 passed, 34 deselected**, exit code 0, 0.15 seconds. This covers NaN, Infinity and -Infinity; each case asserts UNAVAILABLE, ARTIFACT_INVALID_OR_UNREADABLE and content is None.

Full test-file command:

~~~powershell
python -B -m pytest -p no:cacheprovider --tb=short tests/test_control_master_context_reader.py
~~~

Reported result: **37 passed**, exit code 0, 0.70 seconds.

These are OWNER_CODEX_REPORTED results, not a test run performed by this ChatGPT session.

## 5. Acquisition blocker and harness limits

The earlier full clone failed with exit code 128 and No space left on device; the two target files were not materialized in that partial clone. Codex did not retry the full clone. It retrieved the exact two target files from GitHub and ran them in a minimal harness. The harness used its own pytest rootdir and did not load repository-level pytest configuration. Consequently, the result supports the exact reader and test file in that harness, not the full repository configuration, all repository tests, or integration/runtime paths.

The retained harness path reported by Codex is C:\Users\faber\AppData\Local\Temp\m1b-pr555-api-harness-20261028-231820. Cleanup was blocked by policy and was not retried using an alternate deletion method. The prior partial clone at C:\Users\faber\AppData\Local\Temp\m1b-pr555-validation-20261028-231202 was left intact. C:\Python was not touched.

## 6. Limits and preserved invariants

- The residual resolve() to open() filesystem TOCTOU limitation from the static review remains unaddressed by F-01/F-02.
- The mixed line endings in the test file remain a formatting issue from the prior review; no normalization was attempted.
- No full checkout, full-repository test run, build, MCP runtime, tunnel, E2E, protected read, merge, branch rebase, credential creation or bridge activation occurred.
- No tests were run by this ChatGPT session.

~~~text
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
PRODUCT_CANDIDATE_MERGE=NOT_AUTHORIZED
C:\Python=DO_NOT_TOUCH
~~~

## 7. Evidence classification

- VERIFIED: live branch/PR head from GitHub metadata; exact file blob IDs; file SHA-256 calculated by this session; contents show the parser callback and parametrized test.
- OWNER_REPORTED: Codex's Python/pytest version check, harness construction, test commands and outcomes, disk state, retained directory, cleanup-policy rejection.
- INFERENCE: the reported test result supports the repaired parser behavior on the exact files in the described harness, assuming the receipt's execution report is accurate.
- UNKNOWN: whether the suite behaves identically under the full repository pytest configuration and whether residual filesystem race scenarios matter in the target threat model.
- NOT_RUN: independent pytest execution in this ChatGPT session; repository-wide test/build/runtime/E2E.

This receipt records evidence and a bounded method lesson. It does not select the active project route, replace canonical CURRENT-STATE.md, establish G1/G2/G3, or authorize bridge activation.
