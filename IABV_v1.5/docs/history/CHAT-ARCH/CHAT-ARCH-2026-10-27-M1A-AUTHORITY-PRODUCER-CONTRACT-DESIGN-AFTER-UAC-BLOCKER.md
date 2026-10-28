# M1A — Source-derived authority producer contract after UAC execution blocker

- Date: 2026-10-27 (America/Bogota).
- Repository: `jhonf463r/Python`.
- Canonical route authority: `CURRENT-STATE.md`.
- Protocol: `UAAL-CFCP-001`.
- Scope: bounded source-derived design; no product-code changes, no local Windows inspection, no runtime or provisioning.

## 1. Revision-bound evidence

References observed immediately before this note:
- `main=0ebd1d6bd97bfe96423ce62b13dcd525b7b494fa`.
- PR #531: `OPEN/DRAFT/UNMERGED`, HEAD `bc2baf525a70d66628809360a197f25a069aa328`, base `7ddfe285b1a3267f9ef6f57f862cca78bc8438c2`.
- PR #549: `OPEN/DRAFT/UNMERGED`, HEAD `519c55a5b96a5e0b3826b54bf92726ef7f1b9c28`, base `a8624c30744da7f593d6a1c829e48aa229c8efca`.

The local Codex report says that the approved request for `Start-Process -Verb RunAs` was blocked by the execution-tool policy before a process or UAC window started. This is `UAC_REQUEST=BLOCKED_BY_EXECUTION_TOOL_POLICY`, not a user denial. TPM and Secure Boot remain `UNKNOWN`; no hardware evidence was acquired in that attempt.

Sources inspected at the exact PR #531 HEAD:
- [bootstrap.py](https://github.com/jhonf463r/Python/blob/bc2baf525a70d66628809360a197f25a069aa328/IABV_v1.5/src/iabv_v15/bootstrap.py)
- [read_authorization.py](https://github.com/jhonf463r/Python/blob/bc2baf525a70d66628809360a197f25a069aa328/IABV_v1.5/src/iabv_v15/services/security/read_authorization.py)
- [github_owner_merge_bootstrap.py](https://github.com/jhonf463r/Python/blob/bc2baf525a70d66628809360a197f25a069aa328/IABV_v1.5/src/iabv_v15/services/security/github_owner_merge_bootstrap.py)
- [windows_handle_reader.py](https://github.com/jhonf463r/Python/blob/bc2baf525a70d66628809360a197f25a069aa328/IABV_v1.5/src/iabv_v15/infra/mcp/windows_handle_reader.py)
- [server.py](https://github.com/jhonf463r/Python/blob/bc2baf525a70d66628809360a197f25a069aa328/IABV_v1.5/src/iabv_v15/infra/mcp/server.py)

## 2. Causal conclusion

The immediate production blocker does not depend on whether the hardware is TPM-ready: `AppBootstrap` currently creates `ReadAuthorizationCoordinator.unconfigured()`. No positive protected-read path is available. Hardware-backed key selection is a later implementation detail; the first source milestone is to specify and validate the trust-provider contract without inventing a trusted provider.

## 3. Source-derived contracts and missing producers

| Boundary | Source already present | Missing production proof |
|---|---|---|
| G1 root / custody | `TrustAnchor`, `TrustAnchorProvider`, RSA/SHA-256 verification, fingerprint helper | An independently provisioned anchor source with verifiable provenance, lifecycle and revocation. A public-key fingerprint is diagnostic only. |
| Owner / mandate | `OwnerMandate`, `OwnerAuthenticationEvidence`, strict binding validators, fixed repository/Owner identifiers | A production Owner assertion verifier bound to a fresh challenge and relying-party context; caller-supplied identity fields must never be trusted. |
| Issuer credential / process | `ProtectedIssuerCredentialEvidence`, issuer ID/key/server/instance/principal bindings | A protected key provider and independently authenticated host-owned issuer process. A response field `peer_identity` alone does not authenticate the IPC peer. |
| Owner-approved enrollment | `verify_owner_merge()` verifies an exact merged manifest, expected GitHub Owner ID, base/repository, challenge, manifest bytes and main ancestry | `OwnerControlledBootstrapBoundary` is still a `Protocol`; no production implementation performs independently authenticated Owner verification, durable challenge consumption, protected registry mutation or OS peer authentication. Merge evidence is one input, not proof of enrollment. |
| Challenge / registry | Typed challenge, consumption, persistence and enrollment-receipt structures plus binding validators | Real durable challenge store, one-use atomic consumption, protected trust registry and independent evidence that the reported persistence occurred. Value-object receipts do not prove external effects. |
| G2 policy / revocation | `G2PolicySnapshot` validates anchor/source binding, signature, policy/mandate version equality, operation scope, expiry, revocation list and a maximum 24-hour TTL | A production policy provider, authorized publication path, freshness/revocation guarantees and monotonic anti-rollback state. Matching an older policy version to an older mandate does not by itself prove that the policy is the latest accepted version. |
| G3 approved root / target | Server opens an `OpenedTargetCapability`, sends that same object into the authority decision and consumes it through `read_opened_file` / `list_opened_directory` | A host-owned `approved_workspace_root_provider` and production `G3TargetResolver` are not wired. Source-level same-object identity still requires authorized native Windows acceptance; do not infer it from synthetic tests. |
| Replay / rollback | `SQLiteReplayConsumer.consume_once()` uses transactional uniqueness and fails on missing/corrupt/reused state | Production service-owned storage/ACL and rollback-resistant monotonic state. The implementation explicitly does not detect restoration of an older valid SQLite snapshot. |
| Host request identity | `ServerReadRequestContextProvider` protocol and per-request binding fields | A production source of host-owned principal, server, instance and service-fingerprint claims that cannot be asserted by MCP caller input. |

Primary implementation references: [G1 enrollment evidence](https://github.com/jhonf463r/Python/blob/bc2baf525a70d66628809360a197f25a069aa328/IABV_v1.5/src/iabv_v15/services/security/github_owner_merge_bootstrap.py), [authorization coordinator](https://github.com/jhonf463r/Python/blob/bc2baf525a70d66628809360a197f25a069aa328/IABV_v1.5/src/iabv_v15/services/security/read_authorization.py), [bootstrap composition](https://github.com/jhonf463r/Python/blob/bc2baf525a70d66628809360a197f25a069aa328/IABV_v1.5/src/iabv_v15/bootstrap.py).

## 4. Required positive-path contract (not implemented here)

Before any future provider can be injected into production, the implementation and acceptance tests must establish all of the following:

1. **Root provenance:** the active anchor is obtained from a host-owned protected source, carries explicit validity/revocation metadata, and is independently bound to a selected Owner credential. Neither an app-generated fingerprint, GitHub merge event, SID hash nor TPM-provider enumeration is sufficient alone.
2. **Owner proof:** a challenge-bound Owner assertion is cryptographically verified by a production verifier using a separately established Owner credential and exact relying-party context. All principal/credential identifiers are derived from verified evidence, not caller fields.
3. **Issuer boundary:** the issuer key is protected under a documented custody model; the issuer process identity and OS peer are authenticated outside the response payload. MCP reader/requester code gets no registry-mutation capability.
4. **Enrollment transaction:** validate challenge, Owner proof, issuer credential and exact merge evidence; atomically consume the challenge; persist the trust record in protected storage; only then return a typed enrollment receipt. A receipt must identify the transaction and binding/version outcomes without pretending that its own field values prove storage effects.
5. **G2 freshness/revocation:** signature, anchor/source, scope, expiry, revocation and monotonic latest-version checks must pass on each positive decision. If the source cannot prove freshness or monotonic state, deny. The TTL is a bound, not a revocation channel.
6. **G3 identity:** the approved root and resolver must bind target/root/policy/workspace/checkout/server/instance. The object authorized must be the exact object consumed; pathname re-resolution is not acceptable.
7. **Replay/rollback:** consume-once must be atomic and durable; restoration of earlier state must be detected by an independent monotonic mechanism or treated as an untrusted store and denied.
8. **Composition gate:** `AppBootstrap` must not produce a positive coordinator until every exact production provider has passed authenticity/configuration checks. Checking that eight objects are non-null is not enough.
9. **Failure semantics:** missing provider, wrong identity, stale/revoked policy, replay, rollback, forged peer, target mismatch, time failure or persistence ambiguity all lead to denial before protected content is read. No fallback to paths, software keys, a mock provider or the current directory.
10. **Observable evidence:** every acceptance claim records exact SHA, changed paths, command/run, exit code and provenance. Synthetic tests, source review and native Windows acceptance must be reported separately.

## 5. What can continue while hardware discovery is blocked

Allowed without further local permission:
- source-level contract correction and focused synthetic test authoring in a new isolated candidate;
- static review of whether all production composition paths stay fail-closed;
- interface/capability design that keeps hardware custody abstract until independently confirmed;
- documenting a deterministic acceptance matrix and failure semantics.

Not authorized by this note:
- create/import keys or certificates, change TPM/UEFI/Secure Boot, install a service, create IPC endpoints/ACL, create or seed a trust registry/mandate/policy, configure Entra, install packages, run tests/build/runtime, enable protected reads/tools, start tunnel, merge/rebase existing PRs, or activate the bridge.

## 6. Next action and stop condition

Next action is a source-only, revision-bound candidate task for the **contract/composition layer only**, based on a fresh isolated branch from current `main` (not the divergent PR #531 branch). Its changes must remain deny-only and must not add a concrete trust anchor or production provider. It should improve typed missing-requirement reporting and contract tests for enrollment/revocation/rollback boundaries only where a demonstrated source mismatch exists.

If no concrete source defect can be proved without choosing the Owner credential or provisioning a root, stop and provide the minimal explicit design decision required; do not generate more generic review documents. Do not ask the Owner to perform local commands or UI steps. If a future authorized native read requires elevation and tool policy blocks it, classify that as an execution-channel blocker, not an Owner denial.

## 7. Preserved state

```text
UAC_REQUEST=BLOCKED_BY_EXECUTION_TOOL_POLICY
UAC_UI=NOT_SHOWN
TPM=UNKNOWN
SECURE_BOOT=UNKNOWN
G1/G2/G3=NOT_ESTABLISHED
MCP_TOOL_ALLOWLIST=EMPTY
PROTECTED_READS=FAIL_CLOSED
TUNNEL=DISABLED
BRIDGE=BRIDGE_NOT_READY
MERGE=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
```
