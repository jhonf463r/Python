# Owner decision receipt — bounded trust/authorization-organ source implementation

- Decision date: 2026-10-24, America/Bogota
- Decision provenance: explicit Owner message in the current conversation
- Verified live-main baseline when recorded: `fed7d50926a0c09b2fdd2e9d00cc71fa05a3e6d7`
- Status: durable candidate receipt; this is not a runtime identity assertion or proof of a qualifying trust root.

## Decision

The Owner explicitly directed the coordinator to stop looping around the trust/authorization blocker, identify and fix the coordinator's reasoning failure, and proceed with the next concrete task to build the trust/authorization organ needed for the governed IABV bridge.

This authorizes **bounded product source-code changes and source-test authoring** in the existing Owner-reported local Codex candidate. It does not authorize execution or deployment.

## Authorized source scope

- Preserve the existing local candidate work. Its last Owner-reported HEAD is `9803a282760824eae630a27561f6aed6c4b6a6bd`; that ref was not found on remote GitHub during the coordinator check.
- Before editing, verify the Windows Codex session, repository/worktree, current `origin/main`, local HEAD, dirty state and changed paths. Preserve the candidate and reconcile it non-destructively with current main.
- Update the branch-local continuity receipt and state routing to record this new scope; keep the older terminal root-review result in history rather than reusing its old `NEXT_ACTION` as if no new Owner instruction had arrived.
- Implement the source-level trust/authorization organ: real signature verification using already-declared dependencies or existing OS primitives; explicit independent trust-anchor and mandate inputs; exact server, operation, target, policy revision and expiry binding; durable atomic one-time challenge consumption and fail-closed corruption/rollback behavior; source-level authenticated issuer/service boundary and IPC contracts.
- Connect its decision to `read_repo_file` and `list_repo_directory` before file access/listing. Without a verified root/mandate and valid G1/G2/G3 decisions, deny.
- Add or update source tests for positive and negative authorization paths, signature failure, replay, expiry/revocation, mismatched server/target/policy, issuer/IPC failures, absent G2/G3, and proof that the reader helpers are never called on denial.
- Use only already-declared dependencies and existing platform capabilities. Do not invent a root or treat PEM syntax as cryptographic verification. If an isolation primitive cannot be achieved without an OS-level change, implement only a fail-closed source contract and precisely report the remaining boundary.

## Explicitly not authorized

- Test/build/runtime execution; real MCP transport or protected reads.
- Service installation/start, persistent Windows ACL/trust-store changes, credentials or keys generated/stored for production, app registration, public tunnel, deployment, spending, or changes to the machine.
- Publishing the local candidate or opening/merging a product PR without a separate decision.
- Declaring G1, G2, G3, or any of the eight prerequisites closed from source intent.

## Evidence required at return

Return exact repo/session/checkout path, current main SHA, local branch/HEAD before and after, ancestry reconciliation result, working-tree status, paths and blob hashes, code locations for verifier → issuer → IPC → MCP enforcement, tests authored versus run, dependencies, and all remaining root/mandate/isolation gaps. Label the result `SOURCE_CANDIDATE_ONLY`. No gate closure claim.

This instruction changes the scope of source construction, not the truth of the terminal review. `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`, `QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED`, and G1/G2/G3 remain unestablished until independent evidence exists. Deny real reads until then.
