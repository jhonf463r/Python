# Owner decision receipt — reopen one bounded source-organ remediation task

- Decision date: 2026-10-24, America/Bogota
- Decision source: explicit instruction in the current ChatGPT conversation; the user asked to proceed toward finishing the authorization organ or identifying/removing the real blocker to the bridge, and expressly required analysis of existing memory to avoid repeating completed work.
- Provenance: `OWNER_DECISION_IN_CURRENT_CHAT`; the instruction is direct evidence of the requested scope, not independent authentication of a Windows principal or authority asset.
- Canonical baseline revalidated for this intake: `main=053b692213f484fc0d5e79cd3c44ee5c94fb2dcf`.
- Prior terminal result retained: `STATIC_REVIEW_COMPLETE_FOR_SUPPLIED_FULL_DIFF_BUNDLE`; full diff SHA-256 values verified as `cb7db09f3cec514846af4c1c5d449c22d3b2579de94254a95f12b6557050d9c1` and `0af9902c5109841cde9558857e1aacc99c4b620eaff9a0a75a77a1daeef6fdab`. That result is not repeated, and it did not directly inspect the Windows worktree or execute behavior.

## Decision and scope transition

The Owner's new instruction explicitly reopens one bounded source-organ remediation step after the prior source-only attempt had been marked terminal for the evidence then available. It does not introduce new independent root/mandate evidence and does not make the source candidate or bridge ready.

**Permitted for the next bounded task only**
- Work in the existing Windows candidate reported at `C:\\Users\\faber\\AppData\\Local\\Temp\\iabv-g1-bootstrap-sparse-f99534e037e542038513a974d805bb27`, but revalidate the actual path, repository, branch, HEAD, and status at task start. These details remain historical/Owner-reported, not current facts.
- Make a minimal, source-only correction to the existing authorization organ and author focused source tests for confirmed source-level defects from the accepted whole-candidate receipt.
- Reuse the full static review and its finding map; do not rerun the broad 12-path review or ask the Owner for those already supplied diffs.
- Establish a fresh, exact pre-edit baseline for only the files to be changed and return complete diffs against that baseline. Preserve all pre-existing staged changes, HEAD, and the index; do not stage or commit the new edits.

**The first source scope**
1. Fix strict runtime typing for `mandate.revoked` so malformed non-boolean values cannot pass a revocation gate; add focused source tests.
2. Reconcile required `server_id`/`issuer_id` manifest fields with the manifest schema version and all candidate-owned validation/fixtures. Do not assume a deployed consumer is absent; if compatibility cannot be established from permitted evidence, make the versioning mismatch explicit and fail closed.
3. Add the missing explicit source assertion for `AUTHORITY_TARGET_INVALID`.
4. Inspect whether exact-target/same-object binding can be implemented safely using the existing code and platform contracts. The reader must consume the exact identity-bearing target authorized by the decision, not independently resolve the original relative path. If a genuine same-object guarantee requires an unavailable platform boundary, leave the path denied and report the exact dependency; do not emulate success with mocks or claims.

This scope is a bounded reopening, not a blanket authorization to invent the missing trust root. No more source-only iterations are authorized automatically after the result.

## Prohibited / unchanged

```text
TEST_EXECUTION=NOT_AUTHORIZED; NOT_RUN
BUILD=NOT_AUTHORIZED; NOT_RUN
RUNTIME=NOT_AUTHORIZED; NOT_RUN
MCP=NOT_AUTHORIZED; NOT_RUN
REAL_TRANSPORT=NOT_AUTHORIZED; NOT_RUN
PROTECTED_READS=FAIL_CLOSED
CREDENTIAL_CREATION_OR_ENROLLMENT=NOT_AUTHORIZED
SERVICE_INSTALLATION=NOT_AUTHORIZED
OS_ACL_OR_TRUST_STORE_CHANGES=NOT_AUTHORIZED
LIVE_PROCESS_OR_AUTHENTICATED_IPC_SETUP=NOT_AUTHORIZED
PUBLIC_TUNNEL=DO_NOT_LAUNCH
STAGING_OR_COMMIT=NOT_AUTHORIZED
PUSH_OR_SOURCE_CANDIDATE_PUBLICATION=NOT_AUTHORIZED
DEPLOYMENT_OR_SPENDING=NOT_AUTHORIZED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED_UNTIL_EXACT_TARGET_BINDING_IS_EVIDENCED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
BRIDGE=BRIDGE_NOT_READY
COST_POLICY=ZERO_BUDGET
AUTOMATIC_FOLLOW_ON=FALSE
```

The previous whole-candidate review remains complete for its supplied bundle. The current local checkout must be revalidated before editing; do not assume the working tree is unchanged merely because the branch name is familiar. If the baseline differs, inspect only the new delta and affected contracts rather than repeating the completed full review. Any inability to guarantee same-object binding or establish genuine authority must be reported as the blocking dependency—not converted into a positive ALLOW path.

## Required hand-back

Return `TASK_RESULT=BOUNDED_SOURCE_ORGAN_REMEDIATION_CANDIDATE_ONLY`, the exact checkout/repo/branch/HEAD, initial/final status, pre-edit baseline and post-edit hashes, complete affected-file diffs without ellipses, changed-file list, source-test additions, and explicit `NOT_RUN` status for all execution steps. State separately which source defects were corrected and which real trust/platform dependencies remain open. Do not claim the bridge is enabled or any gate has closed.
