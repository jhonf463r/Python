# Independent static review — whole bootstrap-boundary candidate diff bundle

- Date: 2026-10-24, America/Bogota
- Canonical main checked: `2cecd5e9b9e175584d65bbb1198a53bc2346d095`
- Candidate branch/HEAD: `OWNER_REPORTED` — `codex/m1a-g1-owner-governed-bootstrap-organ-20261024` / `6bc568e1c5a898afd65cc045c779c25a9cdc5489`
- Method: read-only inspection of the Owner-uploaded, complete staged/unstaged patch exports; no local Windows checkout was opened.
- Result: `STATIC_REVIEW=COMPLETE_FOR_SUPPLIED_FULL_DIFF_BUNDLE`
- Boundary: static source review only. It is not test, build, runtime, transport or authorization-gate evidence.

## 1. Artifact custody and integrity

The two uploaded diff files were read at their grounded sandbox paths and their SHA-256 hashes independently recomputed.

| Artifact | Lines | Bytes | Independently computed SHA-256 | Codex-reported SHA-256 |
|---|---:|---:|---|---|
| `staged.diff.txt` | 1,899 | 82,068 | `cb7db09f3cec514846af4c1c5d449c22d3b2579de94254a95f12b6557050d9c1` | Same |
| `unstaged.diff.txt` | 3,844 | 168,032 | `0af9902c5109841cde9558857e1aacc99c4b620eaff9a0a75a77a1daeef6fdab` | Same |

This establishes the uploaded bytes match the reported hashes. It does not independently establish the Windows checkout's live status/HEAD, the correctness of Codex's custody report, or execution. The submitted objects are current staged/unstaged diffs, not raw checkout snapshots; there is no pre-task baseline from which to attribute every line to a specific attempt.

## 2. R-01–R-08 findings

| ID | Static finding | Disposition |
|---|---|---|
| R-01 — Owner/root/enrollment | The candidate adds typed evidence, challenge and enrollment contracts, validators and a `OwnerControlledBootstrapBoundary` protocol. The Owner assertion verifier, protected issuer credential provider, challenge store, trust registry and enrollment boundary have no production implementations or enrollment producer in the supplied delta. Reported evidence objects/receipts carry values; they do not prove cryptographic verification or that consumption/persistence actually occurred. | `SOURCE_CONTRACTS_PRESENT`; independent root, Owner identity and G1 enrollment remain `NOT_ESTABLISHED`. |
| R-02 — composition | `AppBootstrap` registers `ReadAuthorizationCoordinator.unconfigured()`; the reference is injected through bridge/runner/server and checked by both MCP protected-read handlers. The coordinator reports seven provider slots as unavailable when not supplied and documents eight missing production requirements. | `SOURCE_WIRED_FAIL_CLOSED`; a configured production authority path is absent. |
| R-03 — protected read / exact target | The handler guard returns `governance_blocked=True` on all paths, including a syntactically valid typed `ALLOW`, which receives `AUTHORIZED_TARGET_NOT_BOUND_TO_OPERATION`. The handlers return this block before calling file/directory helpers. Those helpers still accept the original relative path and resolve the target independently; no identity-bearing G3 handle is passed into the filesystem operation. | `DENY_ONLY_CONTAINMENT`; `SAME_OBJECT_BINDING=NOT_ESTABLISHED`; protected reads remain fail-closed. `AUTHORITY_TARGET_INVALID` appears in source, but no test assertion for that reason appears in the supplied test diffs. |
| R-04 — expected registry | The receipt validator checks reported challenge-consumption and registry-persistence fields and compares `persistence.registry_id` against `expected_registry_id`. The code itself documents that this expected ID must be supplied by future trusted host configuration/provider. | Equality validation is present; a production trusted registry-ID source and independently evidenced durable persistence are absent. |
| R-05 — replay store | `SQLiteReplayConsumer` implements source-level initialization, SQLite integrity/schema checks, unique nonce/decision constraints and transactional consume-once. It explicitly cannot detect restoring an older but internally valid database snapshot. The candidate does not wire a provisioned service-owned database, protected ACLs or a rollback-resistant monotonic source. | Partial source mechanism only; production anti-replay and rollback resistance are `NOT_ESTABLISHED`. |
| R-06 — cryptography | The candidate validates RSA SPKI public keys and uses Windows CNG for RSASSA-PKCS1-v1_5/SHA-256 verification when available. The algorithm verifies a signature under a supplied public key; it does not establish who controls that key or prove an independent Owner trust root. | Signature-verification code is source-present; trust/key provenance and G1 remain `NOT_ESTABLISHED`. |
| R-07 — transport | A `stdio` option exists, but the bridge/server defaults remain `streamable-http`; no restricted-local deployment profile is established or executed. Diff context also shows existing server settings disabling DNS-rebinding protection and allowing wildcard hosts/origins. Those settings are visible in unchanged context, not established as a newly introduced change by this candidate. | Transport safety/profile is `NOT_VERIFIED`; do not launch a public tunnel. |
| R-08 — OS/process boundary | Typed contracts name Owner and issuer identity, but the supplied source has no production Owner-to-Windows-principal binding, independently provisioned root, separate protected issuer process, authenticated OS IPC adapter, process separation, persistent protected ACL or trust registry. | Required real platform boundary remains `NOT_ESTABLISHED`; no positive authorization release. |

## 3. Additional concrete source findings

1. **Manifest schema versioning:** the expected manifest adds mandatory `server_id` and `issuer_id` fields, while `MANIFEST_SCHEMA_VERSION` remains `1` in the staged/unstaged source. This is a contract-versioning risk. Before any published consumer depends on it, either bump the schema version or establish that schema version 1 had no external/deployed consumers.
2. **Strict revocation typing:** `ReadAuthorizationCoordinator.authorize()` checks `anchor.revoked is not False` and `issuer.revoked is not False`, but checks `mandate.revoked` only by truthiness. Python dataclass annotations do not enforce runtime input types; a falsey non-boolean value could pass that one check if a malformed provider returns it. Require exact boolean typing/value before any positive path.
3. **Transport configuration:** the wildcard Host/Origin and disabled DNS-rebinding protection visible in server context remains a risk if an HTTP server is exposed. This review did not execute or expose the transport. Canonical no-public-tunnel policy remains in force.
4. **Test evidence:** tests in the bundle are source authored. No test, build, runtime, MCP session, protected read or real transport was executed during this review.

## 4. State transition

```text
DIFF_BYTES=RECEIVED_AND_SHA256_VERIFIED
STATIC_REVIEW=COMPLETE_FOR_SUPPLIED_FULL_DIFF_BUNDLE
CANDIDATE_WORKTREE_STATUS=OWNER_REPORTED; NOT_DIRECTLY_OBSERVED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
MCP=NOT_RUN
REAL_TRANSPORT=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
QUALIFYING_INDEPENDENT_ROOT=NOT_ESTABLISHED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
BOOTSTRAP_AUTHORITY_TO_ISSUER=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
BUDGET=ZERO
AUTOMATIC_FOLLOW_ON=FALSE
SOURCE_CANDIDATE_MODIFIED_BY_REVIEW=NO
MAIN_MODIFIED_BY_REVIEW=NO
```

## 5. Routing consequence

The supplied candidate does not establish a real Owner-controlled enrollment/issuer/OS trust boundary. The review's exact conclusion is **source contracts plus fail-closed containment, not operational bootstrap**. Under the existing prohibitions, the missing independent root, trusted production providers, OS/process identity, authenticated IPC and protected persistence cannot be replaced by mock providers or additional type declarations. Keep all positive reads denied.

The live canonical `CURRENT-STATE.md` remains authoritative; this receipt and related route edits are documentation-branch candidates only. The next continuity work is a bounded audit of the existing Mente Espacio-Tiempo/continuity mechanisms; it must not override technical gates or create a duplicate memory/orchestrator. Any source change, tests, runtime, transport, platform provisioning or merge requires its own scope reconciliation.

