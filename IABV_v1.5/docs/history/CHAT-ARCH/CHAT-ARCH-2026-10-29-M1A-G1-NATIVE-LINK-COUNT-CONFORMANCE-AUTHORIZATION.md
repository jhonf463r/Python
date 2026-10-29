# M1A G1 — authorized native link-count conformance probe

- **TASK_ID:** `M1A_G1_NATIVE_LINK_COUNT_CONFORMANCE_20261029`
- **Owner authorization:** explicit in conversation, 2026-10-29 (America/Bogota)
- **Status at record creation:** `AUTHORIZED; NOT_RUN`
- **Execution actor:** Codex, existing Windows environment
- **Task mode:** bounded native conformance probe only; no source edits or publication.

## Target identity and preconditions

- Worktree: `C:\\_w\\m1a-composition-r3-20261028`
- Branch: `codex/m1a-current-main-fail-closed-20261028`
- Expected HEAD: `e1b430956146c4aa0cadc1df2c3df92150b7f7ea`
- Target source file: `IABV_v1.5/src/iabv_v15/infra/mcp/windows_handle_reader.py`
- Target test file remains unchanged during this probe: `IABV_v1.5/tests/test_windows_handle_reader.py`

Reported final file SHA-256 values from the previous local receipt:
- reader: `59ede3b64cc20bb71fc6e0300572aab174221e8e9d5abd723b6b62efad46690e`
- test: `ac8b5c101f2cb832debce53586bbffc6dc8272e9cc75e15897479235d56237ff`

Codex must verify exact path, branch, HEAD, status and both source-byte SHA-256 values before execution. If any mismatch, stop and return `BLOCKED_IDENTITY_MISMATCH`. No automatic retargeting.

## Authorized observation

The probe may create one exclusively named temporary fixture directory under the existing Windows user's TEMP directory and create only the files/directories owned by this probe. It must use direct native handle queries to measure `FILE_STANDARD_INFO.NumberOfLinks` and `Directory` for:
- temporary root directory;
- empty child directory;
- child directory containing one nested directory;
- single-link ordinary file;
- ordinary file with a second hard link, if the current volume/filesystem supports it;
- both visible names of that hard-linked file.

Then, using the exact uncommitted reader module from the specified worktree (loaded via that worktree's `IABV_v1.5/src`), exercise `_open_component` only against those probe-owned names and existing real directory handles. Observe whether single-link files are accepted, the hard-linked file is denied with `HARD_LINK_DENIED`, and ordinary directories are accepted or rejected. Capture and verify handle closure for the denial paths. Do not infer a generic NTFS/Windows outcome from another filesystem: record filesystem name, volume and native API errors.

The central acceptance discriminator is whether ordinary directories with `NumberOfLinks != 1` occur in the tested environment and are then rejected by the current unconditional check. If so, report the resulting traversal/listing compatibility failure as a native finding; do not patch or work around it during this task. Hard-link creation unsupported by the actual filesystem yields a partial result for the multi-link case, not a pass.

## Strict boundaries

- No changes to source or test files, no tests/build beyond this one bounded native probe.
- No server start, MCP request, protected read, credentials, enrollment, tunnel or bridge activation.
- No commit, push, merge, rebase, publication or branch switch.
- Do not touch `C:\\Python`.
- Create the fixture in a unique fresh temp folder; close all handles and delete only that exact folder if cleanup is safe. If handles cannot be closed or cleanup cannot safely complete, leave remaining artifacts untouched and report their exact path instead of escalating cleanup.
- Do not clean any pre-existing files/directories.
- Do not declare G1/G2/G3 or protected-read readiness based on this probe.

## Required receipt

Return:
1. `TASK_ID`, observed target identity and both verified source hashes.
2. Windows version/build, Python executable/version, filesystem name and volume for the fixture.
3. Native `FILE_STANDARD_INFO` values (`NumberOfLinks`, `Directory`, query success/error) for every fixture object.
4. Actual `_open_component` outcomes and precise error reasons for files and directories, including whether a returned handle was closed.
5. Whether the hard-link operation was supported and, if so, native observations for both names.
6. Fixture cleanup result and exact artifacts left if any.
7. Evidence labels: `VERIFIED`, `OWNER_REPORTED`, `INFERENCE`, `HYPOTHESIS`, `UNKNOWN`, `NOT_RUN`.
8. `TASK_RESULT=NATIVE_PROBE_COMPLETE`, `PARTIAL`, or `BLOCKED`.

No product-wide security conclusion. The only question is whether the new native link-count check behaves compatibly with ordinary directories while denying an actual multiply-linked file.
