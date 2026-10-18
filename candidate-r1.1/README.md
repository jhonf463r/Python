# R10 v0.7.8 documentary candidate — revision R1.1

Logical contract: `R10_V0_7_8_CONTRACT.md` (`Artifact ID: R10_V0_7_8_CONTRACT`), byte-identical to the frozen original v0.7.8 contract.

Matrix: `R10_V0_7_8_TEST_MATRIX_T123_T246.csv` (124 cases, IDs T123–T246; all `NOT_RUN`).

R1.1 preserves the three R1 scenario/oracle cell changes and adds exactly two `normative_basis` cell updates for T137 and T141. The embedded `R10_V0_7_8_PREFLIGHT_REPORT.md` is the current internal R1.1 static preflight; it replaces the ambiguous pre-R1 snapshot from the R1 package. `R10_V0_7_8_R1_1_MATRIX_DIFF.md` lists the exact R1-to-R1.1 delta and original-to-R1.1 delta. The outer ZIP's size/SHA-256 is recorded only in the external relay report after packaging.

Historical v0.7.2–v0.7.7 artifacts remain under `historical/` and are preserved. This is documentary packaging only: no product code, tests, builds, runtime, integrations, dispatcher, M0A or bridge were run. Status: `PENDING_COORDINATOR_RECHECK`; `GOVERNANCE = KEEP_BLOCKED`; `BRIDGE_NOT_READY`.
