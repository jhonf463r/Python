# M1A G1 — native link-count conformance receipt

- **TASK_ID:** M1A_G1_NATIVE_LINK_COUNT_CONFORMANCE_20261029
- **Adjudication date:** 2026-10-29 (America/Bogota)
- **Input:** Owner-provided Codex native probe receipt in the conversation.
- **Session adjudication:** RECEIPT_COMPLETE; NATIVE_CONFORMANCE_PASS_FOR_REPORTED_FIXTURE_SCOPE
- **Scope:** one Windows 11 build, one NTFS volume and one temporary fixture. No extrapolation to other filesystems/builds.

## Identity and environment

Codex reports the following observations:
- worktree C:\_w\m1a-composition-r3-20261028
- branch codex/m1a-current-main-fail-closed-20261028
- HEAD e1b430956146c4aa0cadc1df2c3df92150b7f7ea
- Windows 11 build 10.0.26300
- Python 3.13.2
- fixture at C:\, volume Windows, NTFS, serial ecb2f3eb
- reader source SHA-256 59ede3b64cc20bb71fc6e0300572aab174221e8e9d5abd723b6b62efad46690e
- test source SHA-256 ac8b5c101f2cb832debce53586bbffc6dc8272e9cc75e15897479235d56237ff

The hashes and execution details remain OWNER_CODEX_REPORTED within this ChatGPT session. They were not independently recalculated or re-executed here.

## Native FILE_STANDARD_INFO observations

Codex reports successful GetFileInformationByHandleEx queries for FileStandardInfo class 1; all listed objects had DeletePending=False.

| Fixture object | NumberOfLinks | Directory |
|---|---:|---|
| Fixture root | 1 | True |
| empty-dir | 1 | True |
| parent-dir | 1 | True |
| parent-dir\inner-dir | 1 | True |
| single.txt | 1 | False |
| multi.txt | 2 | False |
| multi-alias.txt | 2 | False |

The native CreateHardLinkW operation reportedly succeeded, so the multiply-linked file case was available on this tested NTFS volume.

## Observed _open_component outcomes

| Attempt | Reported result | Handle cleanup |
|---|---|---|
| single.txt, file | handle returned | closed; is_open=False |
| multi.txt, two hard links | HARD_LINK_DENIED | closed during denial; is_open=False |
| empty-dir | handle returned | closed; is_open=False |
| parent-dir | handle returned | closed; is_open=False |
| inner-dir, opened from direct parent-dir handle | handle returned | closed; is_open=False |

Within this reported fixture, no directory-traversal compatibility failure was observed: every sampled ordinary directory had one link and was accepted. This is evidence for the tested NTFS volume/build only.

## Query-error exercise

The receipt reports one additional native-handle test in which the query was forced to use an invalid information class 0x7fffffff. Windows returned error 87; the module reported WINDOWS_HANDLE_METADATA_QUERY_FAILED and closed the handle.

**Limitation:** this confirms cleanup on the forced invalid-class query error. It does not simulate a spontaneous failure of a valid FileStandardInfo request. The earlier synthetic test was reported to cover a failure from the valid standard-info request; that remains OWNER_CODEX_REPORTED, not rerun or independently executed here.

## Cleanup and prohibited side effects

Codex reports that it closed all direct and module-created handles, restored in-memory instrumentation, removed both exclusively created temporary directories after verifying closure, and left no fixture files. One initial second-probe attempt stopped at a ctypes-wrapper error before the native operation; its fixture was checked and removed. No source changes, test reruns, build, MCP/server/runtime, protected reads, credentials, enrollment, tunnel, commit, push, merge, or publication occurred. C:\Python was not touched.

## Evidence classification

- OWNER_CODEX_REPORTED: observed Windows/build/Python/filesystem/volume, file hashes, native metadata rows, hard-link creation, component outcomes, error 87, handle-closure observations, temporary cleanup, final worktree status, and no prohibited side effects.
- INFERENCE: the single-link predicate did not obstruct the ordinary directories sampled on this NTFS/build; this is bounded compatibility evidence, not a universal policy proof.
- HYPOTHESIS: none needed for the observed fixture.
- UNKNOWN: behavior on other filesystems, volumes, Windows builds, and concurrent link-count changes.
- NOT_RUN: product build/runtime, MCP server, protected reads, full test suite, CI, and any test on a different filesystem or Windows version.
- VERIFIED_IN_THIS_CHATGPT_SESSION: the submitted receipt is internally coherent with the previously reviewed source diff and has been documented; the local native operations themselves were not independently observed by this session.

## Adjudication

~~~text
TASK_RESULT=NATIVE_PROBE_COMPLETE; OWNER_CODEX_REPORTED
NATIVE_CONFORMANCE=PASS_FOR_REPORTED_FIXTURE_AND_FILESYSTEM_ONLY
F556_01=CLOSED_AT_STATIC_REVIEW_SCOPE
F556_02=CLOSED_AT_STATIC_REVIEW_SCOPE; NATIVE_LINK_POLICY_SUPPORTED_FOR_SAMPLED_CASES
DIRECTORY_TRAVERSAL_COMPATIBILITY_FAILURE=NOT_OBSERVED_IN_SAMPLED_NTFS_FIXTURE
VALID_FILESTANDARDINFO_QUERY_FAILURE=NOT_INDUCED_NATIVELY; SYNTHETIC_COVERAGE_OWNER_CODEX_REPORTED
BUILD/RUNTIME/MCP/PROTECTED_READS=NOT_RUN
CODE_PUBLICATION=NOT_DONE
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
PRODUCT_CANDIDATE_MERGE=NOT_AUTHORIZED
C:\Python=DO_NOT_TOUCH
~~~

## Next causal frontier

The previously identified static findings are closed at review scope, and the native probe report shows the guard behaving as intended on its one tested NTFS fixture. The next decision is no longer another unchanged local test run. It is whether the Owner authorizes moving the already-reviewed two-file candidate from the isolated uncommitted worktree to the existing PR #556 as a reviewable code commit. That action is not authorized by this native-probe authorization and must not be inferred from it. PR #556's remote source candidate remains unchanged; main and the product runtime remain unaffected.
