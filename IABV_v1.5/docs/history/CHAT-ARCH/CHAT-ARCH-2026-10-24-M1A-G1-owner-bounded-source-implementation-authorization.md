# Owner decision receipt — bounded source implementation of the trust/authorization organ

- **Decision date:** 2026-10-24, America/Bogota
- **Decision source:** explicit Owner message in the current conversation
- **Canonical base checked:** `main` at `fed7d50926a0c09b2fdd2e9d00cc71fa05a3e6d7`
- **Decision status:** recorded for continuity; the message is not an independently authenticated runtime identity event
- **Purpose:** advance construction of the IABV trust/authorization organ without pretending its missing trust root already exists.

## Owner instruction and scope interpretation

The Owner instructed the coordinator to continue coherently and get the authorization/trust organ ready so it no longer stalls progress toward the governed bridge.

This is interpreted as explicit bounded authorization for **source-code implementation and source-test authoring** in the existing local Codex candidate. It is not blanket authorization for running code, tests, services, protected reads, credentials, deployment, or changing the machine.

## Authorized

- Continue from the existing Owner-reported local candidate branch `codex/m1a-g1-owner-governed-bootstrap-organ-20261024`, reported HEAD `9803a282760824eae630a27561f6aed6c4b6a6bd`, preserving all local work.
- Fetch/reconcile its ancestry against current `origin/main` and inspect the exact prior diff before editing. Do not discard work or publish it automatically.
- Implement the source-level trust/authorization organ and its interfaces: actual cryptographic verification using already-declared/platform capabilities where safely possible; explicit trust-anchor and mandate inputs; server/operation/target/policy/version bindings; expiration/revocation checks; durable atomic one-time challenge consumption with corruption/rollback fail-closed behavior; and authenticated service-boundary/IPC source contracts.
- Integrate its decision into the two named MCP read paths before filesystem access. A valid decision path may only permit a read when all required roots, mandates, G1/G2/G3 controls, freshness, and exact server/target bindings validate. Missing or unverified trust authority must continue to deny.
- Add or update source tests for positive and negative branches, replay, expiry, mismatched target/server/policy, issuer/IPC failure, G2/G3 absence, and proof the reader is not called on denial.
- Reuse existing dependencies and Windows primitives. If safe cryptographic or isolation primitives cannot be implemented with already-declared/platform capabilities, record the exact missing primitive and keep that branch fail-closed; do not fake success, self-create a trust root, or add a dependency.

## Not authorized

- Executing tests, build, runtime, transport, or any protected read.
- Installing/starting Windows services, changing persistent ACLs, creating or storing real keys/credentials, registering apps, modifying OS trust stores, generating a new authority/root, launching a public tunnel, deploying, publishing the local candidate, creating a product PR, merging, or spending money.
- Treating the Owner's request as evidence that a qualifying independent root/mandate already exists.
- Claiming G1, G2, G3, any of the eight prerequisites, the bridge, or the process boundary is accepted or operationally verified.

## Required source result

Return exact repository/checkout identity, current main SHA, branch/head before and after, whether ancestry reconciliation was non-destructive, clean/dirty state, changed files and hashes, concrete source locations for the verification/issuer/reader chain, tests written versus executed (tests must remain unexecuted under this decision), new dependencies (must be none), and all unresolved platform/root/mandate gaps.

The output must call the result `SOURCE_CANDIDATE_ONLY` until separately reviewed and adopted. It must distinguish a source-level IPC/service design from an installed process isolation boundary. It must not alter the local candidate's fail-closed behavior to permit reads with an unverified or fabricated root.

## State transition

This decision changes the allowed scope for a bounded source implementation and source-test authoring only. It does **not** change:
`AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`,
`QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED`,
`G1/G2/G3=NOT_ESTABLISHED`,
`IMPLEMENTATION_PREREQUISITES=8; CLOSED=0`,
`GOVERNANCE=KEEP_BLOCKED`,
`READ_LIST=FAIL_CLOSED`,
or the prohibition on test execution, runtime, credentials, installation, transport, publication, deployment, spending, and release.

The terminal static root review remains terminal for its reviewed evidence set. This is a **newly authorized source-construction task**, not evidence that its previous finding changed. The running bridge remains `BRIDGE_NOT_READY` until the actual authority and bindings exist and are independently validated.
