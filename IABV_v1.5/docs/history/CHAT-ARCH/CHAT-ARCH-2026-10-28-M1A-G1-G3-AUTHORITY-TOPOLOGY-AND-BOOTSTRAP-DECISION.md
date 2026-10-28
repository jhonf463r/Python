# M1A G1–G3 — Authority topology, bootstrap boundary, and completion path

- Date: 2026-10-28 (America/Bogota).
- Repository: jhonf463r/Python.
- Evidence baseline: live main 79ab8c50eaa7518120d5ebed9db4747d395a21cb; PR #549 519c55a5b96a5e0b3826b54bf92726ef7f1b9c28; PR #555 6c601c99bb9cc2111f9dde2f6986aefcc0393785; PR #556 1ef23ce47fa206fa751d90fd0c92bcab8a902a6b; PR #557 a5ca0e88eed5d80eaa9d7a1e9c535ffe5f960b9f.
- Status: OWNER_REQUESTED_ARCHITECTURE_AND_TRACEABILITY_IMPROVEMENT; DESIGN_PROPOSAL_ONLY; NOT_CANONICAL; NOT_IMPLEMENTED.
- Permission boundary: this document does not provision a trust root, create keys/credentials, configure Entra or Windows, execute tests/runtime, enable protected reads, enable the MCP tool allowlist, enable the tunnel, merge a PR, or authorize bridge activation.
- Governing policy remains OPTION_D=RATIFIED_NO_BOOTSTRAP. This proposal does not change its meaning or ask for re-ratification. A change from absolute prohibition to Owner-controlled enrollment is a distinct policy decision, not an implementation detail.

## 1. Executive finding

G1/G2/G3 are not redundant obstacles to every IABV operation. They are an authorization boundary for bridge-mediated operations that cross into governed local resources or side effects. IABV can continue internal computation and explicitly bounded observation without treating every internal function as an authority-gated read. But any MCP-reachable operation that reads protected workspace/repository content or causes a governed side effect must be mapped to a policy and enforcement class; it must not inherit authority merely because it is exposed by an authenticated MCP server.

The main architectural problem is not a lack of Python classes. The source already contains authority contracts, policy verification and replay-consumer concepts. The production composition intentionally has no trusted G1 provider, G2 policy/revocation provider or G3 approved-root/versioned-target provider. ReadAuthorizationCoordinator.unconfigured() therefore correctly denies requests. Replacing None with a fake provider, treating a Protocol as an implementation, using a GitHub blob hash as authority, or loosening the denial would manufacture readiness rather than establish it.

The previous work has proved that some fail-closed source paths can deny; it has not supplied a legitimate trust-enrollment authority or demonstrated the actual Windows security boundary. The terminal BLOCKED_MISSING_G1_TRUST_ANCHOR and APPROVED_WORKSPACE_ROOT_UNAVAILABLE results must be reused as causal evidence, not repeated as open-ended inventory tasks.

## 2. Why the gates exist and where they should apply

| Layer | Question answered | Applies to | Does not prove |
|---|---|---|---|
| MCP transport authentication, e.g. Entra token validation for Streamable HTTP | Which authenticated client/user is making this request to this API? | HTTP endpoint admission | Permission to read a particular file or execute an operation |
| G1 — governance trust and issuer | Who has legitimate authority to issue IABV mandates, who controls it, and which exact server/principal is bound to it? | Governed operations and their authorizations | Which operations are currently permitted |
| G2 — policy/catalogue and revocation | Which operation classes/producers/targets are allowed under a current, integrity-checked and revocable policy? | Each governed decision | That the implementation consumed the object that was authorized |
| G3 — server-side target binding | What exact operation and target will be consumed, and is the target derived from an approved root rather than caller-supplied scope? | Protected file/directory reads and other target-bound actions | That the caller has authority or the policy is valid |
| Enforcement/receipt | Did the real handler reject before access or consume the same opened object under the current decision? | Every relevant enforcement point | That mocks reproduce Windows kernel semantics |

Consequences:
1. A valid Entra token is necessary for a protected HTTP endpoint but is not a G1/G2/G3 substitute.
2. A pure computation or bounded, non-sensitive observation does not automatically need the same target/handle workflow as arbitrary repository reads. It still needs the correct transport boundary and explicit tool-risk classification.
3. read_repo_file, list_repo_directory, test execution, agent/task dispatch, writing, merge and tunnel operations have different risk. They must not be merged into one allow/deny rule. A low-risk class must not become a hidden path to a higher-risk capability.
4. M1B's fixed-path JSON context reader is narrower than a generic repository-file tool. Its target/schema/freshness checks improve that narrow contract, but do not establish G1 and do not authorize generic protected reads. Reuse/review the existing PR; do not republish it.
5. The tool allowlist must stay empty for governed operations until their own policy and enforcement acceptance criteria are satisfied. This document does not authorize any tool.

## 3. Bootstrap circularity and valid resolution

The present policy correctly rejects implicit/self-issued bootstrap. However, if interpreted as no authority can ever be installed or enrolled by any controlled procedure, the first trust anchor can never exist. That is a design deadlock, not a test failure.

There are only two honest resolution families:

- Existing-root route: discover and verify an already-established independent governance root, Owner mandate and trusted provider. Historical bounded attempts did not find such evidence and explicitly prohibit repeating that inventory without a material change.
- Owner-controlled initial enrollment route: an explicit, separately authorized ceremony uses a trust mechanism that exists outside the new IABV issuer itself to approve the initial authority. This is not automatic bootstrap and must not run from ordinary MCP requests. It requires a new, precisely scoped governance decision because the current Option D boundary does not authorize provisioning.

An application cannot create the fact that its own first key is trusted merely by generating that key. The initial trust decision must rest on an already trusted control plane, such as a deliberately approved local administrator/install ceremony bound to the exact reviewed artifact and displayed key fingerprint, an independently trusted code-signing/enterprise deployment root, or another Owner-selected pre-existing mechanism. Entra can authenticate the Owner, subject to exact issuer/tenant/audience/client/role checks, but Entra login alone does not prove that the local executable is trustworthy or entitled to issue IABV mandates.

The implementation must pick one concrete, evidence-backed route. Trying Entra, then TPM, then GitHub, then a generated key is not a design. A TPM is a possible key-protection provider, not the governance authority; if the required provider is unavailable, the route reports the exact blocker rather than silently degrading.

## 4. Proposed minimum topology

Owner/governance decision
  -> explicit, out-of-band initial trust enrollment
  -> G1 trust anchor + mandate + independently authenticated issuer
  -> G2 versioned policy/catalogue + freshness/revocation
  -> authenticated MCP transport (Entra for HTTP)
  -> server-created operation request
  -> G3 approved root + versioned target resolver; open target once without reading content
  -> G1 mandate + G2 policy decide over the exact operation/target
  -> short-lived permit bound to the same open handle, server instance, policy version, nonce and expiry
  -> same-handle reader/enumerator consumes the object
  -> protected replay/rollback state and durable operation receipt

This is a component topology, not a claim that these production components are already wired. The source candidates contain parts of the contracts, not the whole operational route.

### G1 — evidence and production contract

Required evidence:
- Independently grounded trust-anchor provenance and designated custodian.
- Explicit Owner/governance mandate bound to the Owner's authenticated local principal, issuer key, repository/workspace scope and exact server instance.
- Protected issuer credential and authenticated IPC peer identity; a peer_identity response field is not proof of the IPC peer.
- Fresh challenges, atomic one-use consumption, expiry, rotation and revocation.
- Process/OS separation so an ordinary MCP request, reader, or the same untrusted Python process cannot mint an issuer or rewrite the authority registry.

G1 is not closed by token tests, successful login, a GitHub PR merge, a public-key fingerprint alone, a class named TrustAnchor, or a Protocol without a production provider.

### G2 — evidence and production contract

Required evidence:
- Versioned catalogue/policy signed under the independently established G1 authority.
- Authenticated publisher and producer-class allowlist.
- Integrity, issue/expiry and policy-to-mandate version binding.
- Current authoritative revocation evidence and explicit failure behavior if unavailable.
- Anti-rollback state that cannot be defeated by restoring an older valid SQLite/database snapshot.

GitHub can distribute and review policy bytes, but availability, branch history or blob hash alone is not runtime authority for ALLOW. A bounded SQLite consume-once transaction is not proof of rollback resistance. Use independently governed durable/monotonic state appropriate to the declared threat model, or keep the decision denied.

### G3 — evidence and production contract

Required evidence:
- Production composition wiring an approved-workspace-root provider and versioned server-side operation-to-target resolver.
- Operation and target are derived server-side; caller-provided scope cannot override them.
- Target is opened relative to the approved root and the exact opened object is bound into the authorization decision/permit.
- Final reader/enumerator consumes that same handle, not a re-resolved path.
- Verified handle ownership/lifetime, reparse-point and path substitution policy, cleanup, concurrency and supported filesystem semantics on actual Windows.

A workspace root is a containment anchor, not the independent G1 trust root. Unit tests with synthetic handles/mocks are necessary but do not prove real Windows behavior.

## 5. Tool profiles to prevent over-engineering

Do not apply the maximum authority machinery indiscriminately to every IABV function, but do not create an informal bypass. Define explicit policy classes before enabling tools:

| Profile | Intended scope | Required controls |
|---|---|---|
| OBSERVE | Pure computation and clearly non-sensitive, bounded status only | Explicit tool registration; no file/secret reads or side effects; HTTP transport authentication where HTTP is used; bounded output |
| CONTEXT_ARTIFACT_READ | Fixed, schema-validated, freshness-checked control/portable context artifacts | Explicit artifact IDs; fixed paths; no arbitrary caller path; source identity/freshness checks; governed permission to disclose the selected artifact |
| PROTECTED_WORKSPACE_READ | Generic repository files/directories or other protected local resources | Full G1 + G2 + G3 and same-object reader path |
| EXECUTE_OR_MUTATE | Test/command execution, writing, remote task dispatch, merge, tunnel or other side effect | Separate operation-specific authority, interactive approval/budgets/audit/revocation; never inherit permission from a read profile |

These profiles are proposed policy design, not a present allowlist. Existing fail-closed gates remain authoritative until a separate, exact acceptance/release decision. No test-running/merge/tunnel capability can piggyback on read-only authorization.

## 6. Recommended implementation order

1. Close the architecture decision before another code patch. Confirm the exact permitted initial-trust mechanism and who/what outside the IABV issuer is allowed to approve it. If no independent trust mechanism can be evidenced, report BLOCKED_NO_INDEPENDENT_BOOTSTRAP_AUTHORITY; do not manufacture one.
2. Implement and verify G1 composition only in a fresh isolated branch from then-live main, after explicit authorization for the chosen enrollment mechanism. Connect a real provider, not a protocol stub. Keep protected reads denied.
3. Implement G2 against that G1 provider. Policy publication, version freshness, revocation and anti-rollback must use one consistent authority source.
4. Complete G3 against a concrete approved-root provider. Connect target resolver -> open handle -> decision/permit -> same-handle reader without path re-resolution.
5. Wire the operation-class registry and MCP enforcement points. Confirm every reader/tool/launcher entry path maps to a profile; no fallback launch or alternate path can bypass its gate.
6. Use separately authorized acceptance testing, not an indefinite -x cycle. First deterministic unit contracts; then approved isolated Windows-native tests; then, only after all gates/configuration are accepted, a narrowly scoped localhost integration test. No tunnel.
7. Independently fetch back and review the exact revision and report G1, G2, G3, transport authentication and each tool profile separately.

The reported test failure test_server_rejects_unknown_transport is not a G1/G2/G3 dependency. The test expects transport validation before authorization gating, but the server denied startup because authorization was unavailable. Review the test contract before changing it; do not make it pass by weakening denial. Keep that test issue in M1A validation and do not represent it as authority progress.

## 7. Alternative technologies and selection

- Local Windows issuer + CNG/TPM + restricted service identity + named pipe: preferred when the boundary is this workstation and a genuinely independent approved installation/enrollment path exists. TPM is optional only if the accepted profile permits a software-backed protected key; it is not silently optional if hardware backing is mandatory.
- External managed authorization service/Key Vault: viable if an organization-controlled identity, network/service and budget are approved. It adds operational and financial dependencies and is not assumed available or authorized.
- FIDO2/PIV/Windows Hello: useful Owner-presence/authentication factor; not, by itself, the G1 root, G2 catalogue authority or G3 target resolver.
- GitHub App/protected PRs: useful for source provenance and policy distribution. Merge authority is not automatically runtime read authority.
- In-process Python object or SQLite alone: useful as a local contract/ledger component, insufficient for independent issuer isolation and rollback resistance under the stronger declared threat model.
- A separate MCP extension/client changes the calling surface, not the trust model.

Choose the smallest topology that satisfies the declared threat model, then prove its properties. Do not require TPM, Azure hosting, multiple agents or a new plugin merely because they exist. Do not drop a mandatory gate merely to simplify implementation.

## 8. Exact closure matrix

| Gate | Closure evidence | Fail-closed state until then |
|---|---|---|
| G1 | Verified independent root/custodian/mandate; Owner-to-Windows principal; protected issuer/process/instance binding; lifecycle/revocation | BLOCKED_MISSING_G1_TRUST_ANCHOR |
| G2 | Trusted signed catalogue; authorized publisher/producer classes; fresh policy; authoritative revocation; rollback-resistant policy epoch | BLOCKED_MISSING_G2_POLICY_OR_REVOCATION_AUTHORITY |
| G3 | Approved-root provider; versioned target resolver; native same-handle read evidence on supported Windows/filesystem | APPROVED_WORKSPACE_ROOT_UNAVAILABLE or precise native-platform blocker |
| Transport | Correct token/API audience, issuer/tenant, client and role checks for HTTP; loopback bind; no tunnel | HTTP unavailable |
| Tool profiles | Each tool/call site mapped to explicit risk class; no hidden route/fallback | MCP_TOOL_ALLOWLIST=EMPTY for governed operations |
| Acceptance | Exact revision, reproducible bounded test receipts, independent review and native evidence where required | NOT_ESTABLISHED; no positive release |

A test-suite pass is necessary for implementation quality, not sufficient for authority closure. A design document, branch or PR does not establish a deployed authority provider.

## 9. Decisions and authorization boundaries

Current Option D remains unchanged. Owner-controlled initial enrollment is the only identified path that can resolve the deadlock if no qualifying pre-existing root exists, but it is not authorized by this design record. Before implementation, the Owner/governance policy must explicitly select the trusted out-of-band authority mechanism and permit exactly its enrollment effects. That policy decision is distinct from permission to open protected files, activate the MCP server or enable tunnel/side-effect tools.

No further generic trust-asset inventory, Entra setup, TPM/Hello feasibility survey or broad test rerun is the next action. New technical work must attach to a selected, evidence-backed trust boundary. If the actual runtime/OS authority route is unavailable to the current actor, report that actor/tool boundary and name the exact external producer needed; do not retry alternate readers or invent a new agent.

## 10. Evidence and references

- [PR #549 — Entra HTTP authentication candidate](https://github.com/jhonf463r/Python/pull/549): authentication-only; does not establish G1/G2/G3.
- [PR #555 — bounded context artifact reader](https://github.com/jhonf463r/Python/pull/555): reuse/review this existing candidate; do not republish.
- [PR #556 — fail-closed M1A/M1F composition](https://github.com/jhonf463r/Python/pull/556): intentionally retains an unconfigured coordinator and no positive authority providers.
- [PR #557 — UAAL-D021 route-truth proposal](https://github.com/jhonf463r/Python/pull/557): this design addendum is proposed on that branch, not canonical until authorized integration and fetch-back.
- [Authority Producer Contract after UAC blocker](./CHAT-ARCH-2026-10-27-M1A-AUTHORITY-PRODUCER-CONTRACT-DESIGN-AFTER-UAC-BLOCKER.md).
- [G1–G3 implementation prerequisite matrix](./CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md).
- [Microsoft Entra claim validation](https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation).
- [Windows CNG key storage providers](https://learn.microsoft.com/en-us/windows/win32/seccertenroll/cng-key-storage-providers).
- [Windows named-pipe security](https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights).

## 11. Current evidence boundary

DESIGN=PROPOSED; NOT_CANONICAL
OPTION_D=RATIFIED_NO_BOOTSTRAP; UNCHANGED
OWNER_CONTROLLED_ENROLLMENT=PROPOSED; NOT_AUTHORIZED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
TESTS/BUILD/RUNTIME=NOT_RUN_BY_THIS_DOCUMENT_TASK
MERGE=NOT_AUTHORIZED
