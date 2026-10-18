# R10 v0.7.8 R1.1 internal static preflight

Package label: **R10 v0.7.8 documentary revision R1.1 — bounded traceability/package fixup**.
Status: `PENDING_COORDINATOR_RECHECK`; `GOVERNANCE = KEEP_BLOCKED`; `BRIDGE_NOT_READY`.

This file is the current internal static preflight for this extracted R1.1 package. It supersedes the ambiguous generic/pre-R1 snapshot that was present in R1. The immutable R1 package remains available at its prior commit; this report does not rewrite that history. The outer R1.1 ZIP size/SHA-256 is intentionally not recorded inside its own payload; the relay report records it after packaging.

## Identity and scope

- Logical artifact remains `R10_V0_7_8_CONTRACT`; no contract amendment or logical version change.
- Source package: immutable R1 ZIP at artifact commit `541e150b478bcbf24c739860f799f8e5ef227af7`; source ZIP identity verified before changes as 5,248,720 bytes, SHA-256 `1b18f128ceaadce4a32abe4ec3deb7c08f330aa051c6239e4146f91af575ef1f`.
- R1.1 adds exactly two parsed `normative_basis` cell changes: T137 and T141. It retains the three R1 scenario/oracle changes.
- No other matrix semantics or historical payloads are changed. The current parsed R1-to-R1.1 and original-to-R1.1 cell diffs are in `R10_V0_7_8_R1_1_MATRIX_DIFF.md`.

## Matrix controls

- Strict CSV parser: 124 data rows; 12 fields in header and every data row; unique contiguous IDs T123–T246.
- Every `execution_status` remains `NOT_RUN`.
- T137 `normative_basis`: `§4.1; §4.2; §7; §12; §17.1; §17.2`. These cite its completeness/eligibility basis and the direct pre-allocation rejection, result-state and correlation rules. Its two-stage receipt/capture setup and no-allocation/effect oracle are unchanged from R1.
- T141 `normative_basis`: `§2.2; §4.1; §4.2; §17.2`. This now cites the clause that defines `MATCHED` as a correlation disposition. Scenario, preconditions and oracle are otherwise unchanged from R1.
- Exact parsed comparisons found only those two cell changes from R1 and five total changes from the frozen original v0.7.8 matrix (the three R1 changes plus these two basis additions).

## Contract, manifest and preserved history

- The contract is byte-identical to the frozen original v0.7.8 contract: 60,222 bytes, SHA-256 `f251ad59dfee6a524538b08b034ca895388c03d0427b16a5178eb441a7261419`.
- The package contains 213 files including `R10_V0_7_8_SHA256.txt`; the regenerated manifest covers 212 payload files and omits its self-entry. Every manifest path is unique and each recorded payload length and SHA-256 is recomputed from actual bytes after all payload edits.
- The 201 files under `historical/`, including historical ZIPs and extracted trees, are byte-identical to the R1 source extraction.
- The outer ZIP is verified separately after creation for CRC, unique safe paths and exact member/tree byte equality. Its byte size and SHA-256 are in the external commit-pinned R1.1 relay report, not here.

## Limits

These are documentary/static integrity checks only. They do not prove implementation, test execution, runtime, exactly-once, cross-store atomicity, operational efficacy, validator authority or bridge readiness. No tests, product code, builds, runtime, migrations, integrations, dispatcher, M0A or bridge were run. All 124 cases remain `NOT_RUN`.
