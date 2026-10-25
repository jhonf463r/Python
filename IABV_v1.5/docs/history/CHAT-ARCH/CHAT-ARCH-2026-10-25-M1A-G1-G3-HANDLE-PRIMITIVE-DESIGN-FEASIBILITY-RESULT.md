# G3 handle-backed reader feasibility — static design result

- Date: 2026-10-25, America/Bogota.
- Task: M1A_G1_G3_HANDLE_PRIMITIVE_DESIGN_FEASIBILITY_20261025.
- Result: VIABLE_WITH_CONSTRAINTS.
- Activity performed: static analysis of official Microsoft Win32 documentation and the terminal Codex source report provided in chat.
- Not performed: no local Windows inspection, repository-source edit, source test, test execution, build, runtime, MCP call, real transport or protected read.
- Provenance: prior source call-chain findings and local file hashes are from the Owner-supplied Codex report. The API capabilities below are grounded in official Microsoft Learn documentation linked inline. This receipt does not claim that a candidate implementation exists or that these semantics were tested on the target workstation.

## 1. Decision

G3 is **technically plausible and should not be abandoned**. Microsoft documents a user-mode API path for opening a filesystem object relative to an already-open directory handle:

- **NtCreateFile** is documented under Win32 **winternl.h**; **OBJECT_ATTRIBUTES.RootDirectory** may be a previously opened directory handle, and **ObjectName** is then relative to that directory. Its **FILE_OPEN_REPARSE_POINT** option suppresses normal reparse processing for the object being opened. [Microsoft: NtCreateFile (winternl.h)](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile)
- **ReadFile** consumes the supplied **HANDLE** directly; it does not need to reopen the path. [Microsoft: ReadFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile)
- **GetFileInformationByHandleEx** supports metadata queries against a supplied handle and includes directory-enumeration information classes. [Microsoft: GetFileInformationByHandleEx](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfileinformationbyhandleex)
- **FILE_ID_BOTH_DIR_INFO** is used with directory handles; later calls on the same handle continue enumeration. Its documentation also warns that file identifiers are not guaranteed unique over time and may change, so an ID value alone is not durable proof of identity. [Microsoft: FILE_ID_BOTH_DIR_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_both_dir_info)
- **FILE_FLAG_BACKUP_SEMANTICS** is required for a CreateFileW directory handle. **FILE_FLAG_OPEN_REPARSE_POINT** opens the reparse point itself rather than its target for the object being opened. [Microsoft: CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew) [Microsoft: Reparse Point Operations](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-operations)

The official API contracts establish a plausible design route. They do **not** prove the repository has implemented the route correctly, that all filesystem/provider behaviors are compatible, or that root authority is established. Those require separate implementation review and later authorized tests.

## 2. Proposed contract

### A. Establish a trusted workspace-root handle first

The root directory is a capability anchor, not merely a canonical path string. The caller must supply or derive it from an independently accepted workspace configuration and bind it to the expected volume/workspace identity. The G3 work must not manufacture authority from Path.resolve() or from a locally self-asserted file ID.

A possible local-volume bootstrap is to open the fixed volume root directory, verify the expected volume identity against the approved workspace policy, and walk the configured workspace-root components relative to that held handle. Reject UNC/network roots, drive-relative forms, device namespaces, volume-mount paths, and any other root forms outside an explicitly tested support matrix. If no trusted expected root identity/configuration is available, deny.

The IABV independent trust root/mandate and issuer/server chain remain unresolved. The filesystem workspace handle must not be confused with, or used to replace, that separate authority root.

### B. Resolve each relative path one component at a time

1. Parse the request as a relative path using a strict Windows-specific grammar. Reject absolute/UNC/device paths, drive prefixes, alternate data streams (:), empty components, embedded separators in a component, . and .., NULs, and ambiguous names. Do not rely on canonicalization or a pre-open path existence/stat check to establish containment.
2. Starting from the approved root handle, call user-mode NtCreateFile with RootDirectory set to the already-open parent directory handle and ObjectName containing exactly one child component (never a multi-component suffix). Use FILE_OPEN and least-privilege access rights; require directory type for intermediate components and file type for a final file where applicable.
3. Use FILE_OPEN_REPARSE_POINT for each individual component, then query the opened object through that handle (for example FileAttributeTagInfo) before it is ever used as the next RootDirectory or a read target. Default policy: reject every reparse point, including symbolic links, junctions, mount points and unsupported/custom tags. Do not inspect a component by pathname after opening it.
4. Preserve the parent handles needed for the walk until the child has been opened and validated. Close all owned handles deterministically on success and every error path. Keep handle ownership, duplication and concurrency explicit; do not pass an integer that can refer to a closed/reused handle as an untracked capability.
5. If a component open, type check, attribute/tag query, or supported-filesystem check fails or has ambiguous semantics, return DENY. No path-based fallback is permitted.

Why one component at a time: FILE_OPEN_REPARSE_POINT affects the object being opened. A single CreateFileW(full_path, ...) call does not give the caller an opportunity to inspect each intermediate path component before resolving the next one. A relative-handle walk makes each component the object being opened and inspected.

### C. File read consumes the exact authorized handle

After authorization binds to the opened final file handle, obtain required metadata by handle, enforce the byte limit and type policy, and call ReadFile (or a demonstrably handle-preserving wrapper) on that same handle. Do not call Path.read_text, open(path), stat(path), or any equivalent pathname-based helper after authorization. If an adapter must produce a Python file object, prove that it wraps the same native handle and define single-owner close semantics; the simpler primitive contract is for the reader to accept the native handle directly.

The handle binds object identity, not necessarily a content snapshot. The final design must specify share modes and writer/race assumptions. If a consistent immutable byte snapshot is a requirement, that is a separate invariant and must not be silently inferred from “same handle.”

### D. Directory enumeration consumes the exact authorized directory handle

Use GetFileInformationByHandleEx with a directory-information class (for example FileIdBothDirectoryInfo) on the authorized directory handle. Subsequent enumeration calls must use the same handle. Do not use os.listdir(path) or path-based child metadata checks. Enumeration metadata is not itself an open child capability: if a child is to be read or recursively traversed, open that single child name relative to the directory handle, validate the resulting handle, then authorize and consume that same child handle.

Do not use the returned file ID as the sole proof that a later path-based open selected the same object. Microsoft documents possible ID reuse/change over time. Handle continuity is the primary invariant; IDs may supplement diagnostics or compare independently opened handles only with supported filesystem semantics.

## 3. Invariants and adversarial conditions

A future source candidate must state and preserve all of these:

- **Root authenticity:** the workspace-root handle is bound to an expected approved root/volume identity; path normalization is not authority.
- **No path re-resolution:** after a component is authorized by handle, no second pathname lookup can select the consumed object.
- **Every-ancestor inspection:** each ancestor is opened relative to the held parent, with its type and reparse status checked before descent.
- **Reparse policy:** default deny for all reparse points and volume/mount transitions; support requires a separately justified tag-specific design.
- **Name grammar:** reject traversal components, device/UNC/drive prefixes, ADS, separators in a component and ambiguous Windows path forms.
- **Exact consumption:** file bytes are read via the same file handle that was authorized; a directory is enumerated via the same directory handle that was authorized.
- **Lifetime and ownership:** the handle cannot be closed/reused while the authorized operation uses it; every success/failure path closes each owned handle exactly once.
- **Fail closed:** unsupported Windows/filesystem/provider behavior, identity-query failure, invalid handles, access conflicts, parse ambiguity or any type/reparse uncertainty deny the entire request.
- **Bounded I/O:** metadata and content limits are derived from the opened handle, and the read does not exceed approved caps.
- **Concurrency semantics:** define whether authorization permits reading the opened object even if it is renamed afterward, and whether concurrent in-place writes must be excluded. A stable handle is object identity, not an atomic content snapshot.
- **Hard-link policy:** decide whether authorization is by a name under the workspace or requires the object to have no aliases outside it; same-object handles alone do not prove exclusive namespace membership.
- **Supported filesystems:** define an explicit support matrix. Begin with the exact local filesystem/version actually supported by the product; deny unknown or unvalidated remote, removable, virtual or third-party filesystems until their semantics are reviewed.

## 4. API alternatives adjudicated

| Candidate | Finding | Decision |
|---|---|---|
| CreateFileW(full_path) + FILE_FLAG_OPEN_REPARSE_POINT | Opens an object handle, but a single full-path open does not inspect each intermediate component with the needed handle-relative invariant. | Insufficient by itself for rooted untrusted-path traversal. |
| ReadFile(handle) | Reads through the supplied file handle. | Preferred file-content primitive after secure open and authorization. |
| GetFileInformationByHandleEx(FileIdBothDirectoryInfo) | Enumerates using the directory handle; repeated calls continue the enumeration. | Preferred directory-enumeration primitive after secure open and authorization. |
| File ID from enumeration + OpenFileById | Opens by ID on a volume/share, not relative to the authorized directory handle; the ID alone is not durable proof over time. | Not the primary containment/traversal primitive. |
| NtCreateFile with RootDirectory=parent_handle, single-component name, FILE_OPEN_REPARSE_POINT | Microsoft documents the user-mode API and handle-relative object-name semantics. Opening each component separately allows inspection before descent. | Best candidate for a narrow implementation prototype; source and platform behavior still require review and tests. |

References: [NtCreateFile](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile), [CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew), [ReadFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile), [GetFileInformationByHandleEx](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfileinformationbyhandleex), [FILE_ID_BOTH_DIR_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_both_dir_info), [OpenFileById](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-openfilebyid).

## 5. Implementation acceptance plan — proposed, not authorized or executed

A separate Owner decision would be required before any source implementation. That task should be limited to a source-only candidate and directly related test authoring. It must not run tests/build/runtime or perform protected reads.

Required source-level regression cases to author later:

1. File reads pass the authorized opened handle to ReadFile; patched/spy path helpers prove no post-authorization re-resolution.
2. Directory enumeration uses the same directory handle for each continuation; there are no os.listdir(path) or path-based child-stat calls.
3. Intermediate and final symbolic links, junctions, mount points and reparse points are denied.
4. Absolute, UNC, device, drive-relative, .., ADS and malformed multi-component input are denied.
5. Component substitution / rename / delete races cannot cause the reader to consume a different object from the one authorized; where the contract cannot ensure a condition, the operation denies or the threat-model assumption is explicit.
6. A child is not trusted solely because its name/file ID appeared in an enumeration result; recursively consumed objects must be opened and checked by handle.
7. Handles close exactly once and remain valid throughout the operation; failed intermediate opens do not leak prior handles.
8. Unsupported API/filesystem or failed handle metadata queries return deny; no legacy path fallback occurs.
9. Read byte limits are enforced using handle-derived metadata and the same authorized handle.
10. Adversarial content mutation and hard-link expectations are explicitly tested or identified as out-of-scope policy constraints.

All these are acceptance criteria only; no tests were authored or executed during this static feasibility task.

## 6. Dependencies that this design does not close

- G1: independent authority root, custodian and mandate.
- Owner identity bound to the Windows principal.
- Authority/mandate bound to the issuer and exact server instance.
- G2: production policy/revocation authority and binding.
- Durable challenge/replay persistence and rollback resistance.
- The authorized workspace-root handle and its expected identity must be connected to the actual owner-governed policy; a pathname alone cannot stand in for that binding.
- Correctness under the target Windows version and filesystem must be verified by a later, explicitly authorized implementation review/test cycle.

A successful G3 source candidate does not enable protected reads while these separate gates remain open.

## 7. Final routing result

~~~text
TASK=M1A_G1_G3_HANDLE_PRIMITIVE_DESIGN_FEASIBILITY_20261025
TASK_RESULT=VIABLE_WITH_CONSTRAINTS
ACTIVITY=OFFICIAL_API_STATIC_ANALYSIS_AND_CONTRACT_PROPOSAL
SOURCE_CHANGES=0
SOURCE_TESTS=NOT_AUTHORED; NOT_RUN
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED; FEASIBLE_DESIGN_CANDIDATE_IDENTIFIED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
COST_POLICY=ZERO_BUDGET
AUTOMATIC_FOLLOW_ON=FALSE
NEXT_ACTION=OWNER_DECISION_REQUIRED_TO_AUTHORIZE_ONE_BOUNDED_G3_NTCREATEFILE_SOURCE_CANDIDATE_OR_KEEP_BLOCKED
STOP_CONDITION=NO_IMPLEMENTATION_WITHOUT_NEW_EXPLICIT_SCOPE; KEEP_PROTECTED_READS_DENIED
~~~
