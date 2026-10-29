# M1A G1 — independent static adjudication of F-556-01/F-556-02 repair diff

- **TASK_ID:** `M1A_G1_F556_01_02_INDEPENDENT_STATIC_DIFF_ADJUDICATION_20261029`
- **Date:** 2026-10-29 (America/Bogota)
- **Review mode:** static review of the eight consecutive patch blocks pasted by the Owner from Codex's exported unified diff.
- **Source of artifact metadata:** Codex receipt remains `OWNER_REPORTED`; no binary .patch attachment was available to this reviewer.
- **Verdict:** `F556_01=CLOSED_AT_STATIC_REVIEW_SCOPE; F556_02=CLOSED_AT_STATIC_REVIEW_SCOPE; NATIVE_WINDOWS_CONFORMANCE=NOT_RUN`.

## Identity and artifact claims

Codex reported:
- worktree `C:/_w/m1a-composition-r3-20261028`
- branch `codex/m1a-current-main-fail-closed-20261028`
- HEAD `e1b430956146c4aa0cadc1df2c3df92150b7f7ea`
- only these files changed: `IABV_v1.5/src/iabv_v15/infra/mcp/windows_handle_reader.py`, `IABV_v1.5/tests/test_windows_handle_reader.py`
- external patch artifact `C:/_w/M1A_G1_F556_01_02_EXACT_DIFF_REVIEW_20261029.patch`, 61,881 bytes, 1,555 lines, SHA-256 `59a378a8465b454e170db7ee3a6461aa6129c4c6867b14aab66bc22b19d5946b`.

These local filesystem properties, digest, byte match, line count and test results are `OWNER_CODEX_REPORTED`; this reviewer did not open the local artifact or independently recompute its whole-file hash. The complete patch was provided in eight consecutive code blocks in the conversation and inspected as presented. The patch headers name base blobs `cf3045be70e6824bdcc627ccefa14ea33faf6342` and `9f273f5bac57b3eed6fa3e9253b526f690b9766a`, and final blobs `2facf2a4447d1acff69b1845390355902160dbfa` and `1e72fc6e50a91678964bed38b05b82a9d8a4683f`; the current GitHub PR #556 branch has not received these local changes.

## F-556-01 — cap+1 directory listing

**Static result: CLOSED_AT_STATIC_REVIEW_SCOPE.**

In `_list_opened_directory_handle`, an entry is appended and the first count above `cap` now raises `WindowsHandleReaderError("AUTHORIZED_DIRECTORY_ENTRY_LIMIT_EXCEEDED")`. There is no return of the accumulated `entries` list from that branch. The only successful return occurs after enumeration completes and sorts entries by `name`. Thus at source level, cap+1 no longer returns the partial, unsorted list found in the reviewed parent.

Added tests:
- `test_directory_enumerator_returns_sorted_complete_result_at_exact_cap`: checks sorted names and `truncated is False` at a synthetic cap of 3.
- `test_directory_enumerator_denies_without_partial_names_at_cap_plus_one`: checks the denial reason and that the denial payload has no `entries` or secret names.
- `test_mcp_directory_response_omits_entries_when_reader_denies`: invokes the registered server tool through stubs, checks no `entries`/names in the returned denial, and checks target closure.

The effective cap expression `max(1, min(max_entries, 200))` remains unchanged in the patch. The added boundary test uses smaller synthetic caps rather than a 200/201-entry fixture. This is not a source defect in the reviewed branch, but exact-ceiling regression coverage could be stronger. No tests were executed by this reviewer; the previously reported 30-pass run remains `OWNER_CODEX_REPORTED`.

## F-556-02 — enforce single-link policy

**Static result: CLOSED_AT_STATIC_REVIEW_SCOPE; native policy conformance remains unverified.**

`_open_component` queries `_FILE_STANDARD_INFO`, rejects `standard.NumberOfLinks != 1` with `HARD_LINK_DENIED`, and only then checks `standard.Directory`. The rejection is inside the existing `try/except BaseException` cleanup region. A failure in the standard metadata query raises before the handle can be returned and follows the same cleanup path.

Added tests:
- `test_open_component_enforces_single_link_policy_and_closes_denied_handle` covers synthetic `NumberOfLinks=1` success and `NumberOfLinks=2` denial with handle closure.
- `test_open_component_denies_when_standard_metadata_query_fails_and_closes_handle` checks tag-info followed by standard-info query failure and closes the handle.

The policy check is applied to every component opened by `_open_component`, including parent/final directories. These synthetic tests use a file (`directory=False`) and do not exercise native values for ordinary directories. Microsoft's `FILE_STANDARD_INFO` documentation defines `NumberOfLinks` as the number of links to the file, and Microsoft's hard-link overview says NTFS hard links cannot reference directories:
- https://learn.microsoft.com/windows/win32/api/winbase/ns-winbase-file_standard_info
- https://learn.microsoft.com/windows/win32/fileio/hard-links-and-junctions

Those sources establish the documented API meaning and the directory hard-link limitation, but do not substitute for observing `GetFileInformationByHandleEx(FileStandardInfo)` on the supported native Windows/filesystem environments. A native conformance check for ordinary intermediate and final directories is still necessary before any runtime claim.

## Additional review notes / evidence limits

1. Error propagation: the changed reason is raised without a name-bearing detail. The new server-stub test asserts the response contains no `entries` or secret names. This establishes the tested stub path, not a live MCP process.
2. Handle cleanup: the new error path is inside the pre-existing cleanup boundary; synthetic tests exercise close on link-count denial and standard-info query failure. Native handle lifecycle and races remain untested.
3. Link count is checked once after opening and querying metadata. This patch does not prove the value cannot change under all native concurrency/handle-sharing scenarios; do not claim race-free native containment from this static review.
4. The pasted diff visually displays a few added blank lines as `+ ` (plus a space), although Codex reports `git diff --check=0`. Since the binary patch was not attached and its SHA-256 was not recomputed here, whether these visible spaces are literal patch bytes or a transfer/rendering artifact remains `UNKNOWN`. This is not adjudicated as a source defect; preserve the reported diff-check as `OWNER_CODEX_REPORTED`.
5. The reviewer did not run pytest, native Windows code, build, server, protected reads, CI or runtime.

## Evidence classification

- `VERIFIED_FROM_VISIBLE_DIFF`: cap+1 now raises rather than returning partial entries; normal list sort remains before successful return; link-count check follows the standard-info query and rejects values other than one; query/link rejection resides within existing cleanup handling; the stated new assertions are present in the provided test diff.
- `OWNER_CODEX_REPORTED`: exact local path/branch/HEAD/status, complete artifact, digest/size/line count, byte identity with Git output, `git diff --check=0`, and the earlier `30 passed in 0.85s`.
- `INFERENCE`: the actual configured server path returns the denial envelope without listing names, supported by the stub-path test but not a live server observation.
- `UNKNOWN`: native directory `NumberOfLinks` values across supported filesystems; link-count stability under native concurrent operations; whether displayed `+ ` lines are literal artifact bytes.
- `NOT_RUN`: new test execution, native Windows conformance, build, live MCP runtime, broader integration, protected reads and CI.

## Route and invariants

```text
F556_01= CLOSED_AT_STATIC_REVIEW_SCOPE
F556_02= CLOSED_AT_STATIC_REVIEW_SCOPE
TARGETED_TESTS=30_PASSED; OWNER_CODEX_REPORTED; NOT_RERUN
GIT_DIFF_CHECK=PASS; OWNER_CODEX_REPORTED
ARTIFACT_SHA256=59a378a8465b454e170db7ee3a6461aa6129c4c6867b14aab66bc22b19d5946b; OWNER_CODEX_REPORTED
PATCH_BYTES_RECOMPUTED_BY_REVIEWER=FALSE
NATIVE_WINDOWS_CONFORMANCE=NOT_RUN
EXACT_PR_556_SOURCE_PUBLICATION=NOT_DONE
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_CANDIDATE_MERGE=NOT_AUTHORIZED
C:\\Python=DO_NOT_TOUCH
```

**Next causal frontier:** native Windows/filesystem conformance for the enforced link-count rule, including ordinary intermediate directories and target files, plus any race-specific acceptance required by the current security contract. This step is not authorized here, so no runtime or extra test was run. Until that separate authorized gate, source-level F-556 omissions may be considered fixed for static review, but G1/G2/G3 remain unestablished and protected reads remain fail-closed.
