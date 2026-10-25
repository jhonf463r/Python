# Owner decision — one G3 source-candidate task

Date: 2026-10-25 (America/Bogota)

Decision: OWNER_EXPLICIT_SCOPE_APPROVED_IN_CHAT. The Owner replied “si autorizo, procede” to authorize exactly one source-only G3 candidate based on the static feasibility receipt. Source changes and directly related source-test authoring are permitted. Test execution, build, runtime, MCP, real transport and protected reads are prohibited. This receipt records the in-chat decision; it is not an independent identity attestation.

Task: M1A_G1_G3_NTCREATEFILE_HANDLE_RELATIVE_SOURCE_CANDIDATE_20261025.
Baseline main SHA: 45802a266eea9db504f194261ebbf6509281e68b.
Design: CHAT-ARCH-2026-10-25-M1A-G1-G3-HANDLE-PRIMITIVE-DESIGN-FEASIBILITY-RESULT.md.

## Existing candidate — must revalidate before edits

Previously reported, not independently re-observed here:
- Checkout: C:/Users/faber/AppData/Local/Temp/iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27
- Branch: codex/m1a-g1-owner-governed-bootstrap-organ-20261024
- HEAD: 6bc568e1c5a898afd65cc045c779c25a9cdc5489
- Status: 7 staged routes, 11 unstaged, 12 unique.
- Index SHA-256: 8a32e6f7b2d642ee4a0217f96df037497cf47ecac52cecbea08717d4b8cb301a.

If path, branch or HEAD mismatch, or preservation cannot be demonstrated, stop with BASELINE_MISMATCH_NO_EDITS. Do not change checkout, index, staged state, or unrelated work. Preserve pre-edit target-file bytes outside the checkout and hash them. Provide the task diff against those pre-edit bytes, separate from pre-existing staged/unstaged diffs.

## Authorized scope

Inspect only the direct G3 call chain, expected around audit_tools/__init__.py, server.py and directly related source tests. Every changed file must be justified.

Implement a genuine handle-relative, same-object source candidate only if correct native ABI, access flags, metadata checks and lifetime semantics can be implemented safely. Primary design: open one path component at a time relative to the already-held parent directory handle (NtCreateFile/OBJECT_ATTRIBUTES.RootDirectory); reject each component if it is a reparse point; validate through the returned handle before descending. Final file bytes must be read from the exact authorized handle; directory enumeration must use the exact authorized directory handle. No path-based read/stat/listing after authorization.

Never treat a canonical path, Path object, copied file ID, stat result, or wrapper that later re-resolves the path as a handle capability. Do not pass a multi-component untrusted path in one relative open. Define ownership/close-once behavior and preserve bounded I/O. Reject traversal, absolute/UNC/device/drive-relative paths, ADS, malformed components and unsupported platforms/filesystems. Fail closed on API/ABI uncertainty, metadata-query failures, reparse points and unsupported types; do not add a legacy path fallback. The workspace-root handle must remain tied to an approved existing policy; it is not an IABV authority root. Specify concurrent modification and hard-link assumptions rather than claiming a content snapshot.

If safe implementation cannot be supported by the current code, return a precise blocker with no unsafe fallback. A source candidate is not G3 closure or runtime proof.

## Source tests permitted

Author or adjust directly related source tests for exact handle propagation, no path re-resolution, directory enumeration on the same handle, reparse/traversal denial, unsupported-platform/API-failure denial, handle lifetime/cleanup, and preservation of existing deny behavior. Do not run any tests. Mocks do not prove Windows kernel semantics.

## Forbidden

No tests/build/compile/runtime, MCP, real transport, protected reads, credentials, trust-root creation, TPM/Entra, Windows services, ACL/registry/IPC provisioning, OS/network/tunnel changes, spending, staging, committing, pushing, publication, merge or deploy. Do not repeat the prior feasibility review or inventory.

## Required terminal hand-back

Return one TASK_RESULT with actual pre/post checkout, branch, HEAD, status and index hash; complete unabridged task diff against byte-preserved pre-edit files; all file/diff SHA-256 values; original staged/unstaged state preservation evidence; changed-file rationale; source-level result and unresolved limits.

Classify truthfully, e.g. G3_HANDLE_CONTRACT_SOURCE_ONLY_CANDIDATE, PARTIAL_G3_HANDLE_CONTRACT_SOURCE_ONLY, BLOCKED_ON_NATIVE_HANDLE_BINDING_DETAILS, BLOCKED_ON_PLATFORM_HANDLE_SEMANTICS, NO_SOURCE_DELTA or BASELINE_MISMATCH_NO_EDITS.

Required state:
SOURCE_TESTS=AUTHORED_OR_UNCHANGED; NOT_RUN
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_SAME_OBJECT=NOT_ESTABLISHED unless adequately supported
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
COST_POLICY=ZERO_BUDGET
PRODUCT_STAGE_COMMIT_PUSH_MERGE=NOT_AUTHORIZED
AUTOMATIC_FOLLOW_ON=FALSE

Stop after the one report. No follow-on task is authorized. Any candidate remains non-canonical until independently reviewed and adopted. Resolving G3 would not resolve the independent root/mandate, Owner-to-Windows principal, G2 production authority, issuer/server binding or rollback-resistant replay.
