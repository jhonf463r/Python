# M1F — PR #531 bounded static review outcome and route decision

Date: 2026-10-26  
Review ID: `M1F_PR531_R01_R08_BOUNDED_STATIC_REVIEW_20261026`  
Mode: source/patch read-only; no test execution; no source modification.

## Scope and confidence

This is a bounded static review of the R-01–R-08 acceptance boundaries, the transport/source composition, and the material test changes in the exact candidate PR. It is not a claim of exhaustive line-by-line proof over every one of the PR's approximately 5,700 additions. The actual diff and exact-ref source/test files were fetched from GitHub. No pytest, build, runtime, MCP transport or Windows native operation was run.

## Live references

- `main` immediately before this documentation-only route transition: `125e47260714d6adbeacc40fd4245fe9ac5063a7`.
- PR [#531](https://github.com/jhonf463r/Python/pull/531): `OPEN`, `DRAFT=TRUE`, `MERGED=FALSE`.
- Candidate HEAD: `50cbd2b8b3d643d05726290c76ef13f85731949e`.
- Public infrastructure escalation [Community discussion #211346](https://github.com/orgs/community/discussions/211346) is a parallel track, unanswered at publication.
- Actions usage remains `UNKNOWN`: the authorized usage call returned HTTP 404 without values. Diagnostic run 40386434070 is a probe-branch startup failure with no jobs; it is not candidate test evidence.

## R-01–R-08 bounded disposition

| Gate | Source-level status observed | Remaining acceptance boundary |
|---|---|---|
| R-01 / G1 — trust root, Owner mandate and enrollment | Merge/manifest verification and binding validators are present. Tests cover manifest/merge mismatches and strict metadata. | Production Owner assertion verifier, independently rooted trust registry, challenge store/consumer, issuer credential provider, enrollment producer and authenticated authority provenance are not wired. A GitHub merge/valid signature alone is not an independent trust root. |
| R-02 — composition | Bootstrap passes a concrete coordinator into the bridge/server. The bridge checks coordinator type, eight required slots, and root-provider interface before starting transport. | Production bootstrap still explicitly installs `ReadAuthorizationCoordinator.unconfigured()`; the dependency gate proves presence only, not provider authenticity. |
| R-03 / G3 — exact target and handle | Permit, guard, resolver and reader source bind to the same `OpenedTargetCapability`; tests now deny mismatched or forged-looking permits and deny reads before authority. Handle-backed file and directory readers are source-present. | Synthetic source contracts do not establish native Windows object identity, reparse behavior, concurrent lifetime, or actual kernel/ACL behavior. |
| R-04 — expected registry identity | Receipt validation requires a nonblank expected registry ID and exact equality; manifest digests/blob IDs and positive strict-int PR numbers are validated. | The expected ID must originate from an independently trusted host provider. The receipt validators check structure/bindings; they do not prove external challenge consumption or registry persistence happened. |
| R-05 — replay and anti-rollback | SQLite uses transactional consume-once and uniqueness checks; missing/corrupt/reused state denies. Tests are authored for one-use and concurrency. | The implementation explicitly cannot detect restoring an older valid database snapshot. Service-owned storage, restrictive ACL/process boundary and rollback-resistant monotonic state are not established. |
| R-06 — crypto | RSA SPKI parameters are constrained and Windows CNG verifies RSASSA-PKCS1-v1_5/SHA-256 signatures. | Cryptographic validity under a supplied key does not prove that key is trusted, belongs to the Owner, or carries an applicable mandate. CNG/native tests were not executed here. |
| R-07 — transport profile | The candidate removes wildcard Host/Origin acceptance, enables DNS-rebinding protection and allows only local host/origin values. This is the safer local default. | The bridge still defaults to `streamable-http` plus a Cloudflare tunnel with a public, potentially changing hostname. The current local-only allowlist does not implement an approved external-host/origin/authenticated-tunnel profile. The transport objective therefore remains unresolved. Do not use wildcard allowlists or disable protection to make the tunnel work. |
| R-08 — platform/identity boundary | Contracts for host identity and issuer IPC are defined and the normal route fails closed when providers are absent. | A real authenticated issuer process/IPC, Owner-to-Windows principal binding, protected credential process, persistent trust/registry ACLs and rollback-resistant store are external platform/security prerequisites. |

## Test delta — no evidence of a weakened assertion, with a coverage caveat

The relevant edited `test_mcp_server.py` cases changed from pathname-based happy-path expectations to explicit denial when no approved root/authorization provider exists. Those changes match the new fail-closed contract; they are not evidence that tests passed. Added assertions prevent read helpers from being called on absent authority, mismatched target bindings, invalid permits or forged-looking container claims. Bridge tests inject presence-only test objects to exercise unrelated lifecycle paths; these fixtures do not establish a real provider.

The corresponding functional positive end-to-end path through a production-configured coordinator remains unavailable and untested. The tests are authored, not executed, and no test outcome is promoted here.

## Newly adjudicated integration gap — R-07

The code currently combines:
- MCP transport security allowlists restricted to `localhost`, `127.0.0.1`, `[::1]` and local HTTP origins;
- a bridge default transport of `streamable-http`; and
- a Cloudflare Tunnel runner that publishes an external tunnel URL.

The MCP Python SDK documentation states that Host/Origin checks are evaluated against incoming request headers and that an external real hostname must be explicitly allowlisted; otherwise requests are rejected (commonly `421 Invalid Host header`). See the [official SDK deployment guidance](https://py.sdk.modelcontextprotocol.io/run/deploy/).

Thus the candidate has made the unsafe wildcard configuration fail closed, but has not completed the bridge's remote transport profile. A follow-on must first decide the intended governed route: local-only stdio/local access with no public tunnel, or an explicitly authenticated and narrowly allowlisted remote deployment. For a remote route, the exact public hostname/origin, lifecycle order, authentication and threat model must be specified; do not invent an allowlist or bypass DNS-rebinding protection. This is a source/design integration issue distinct from G1/G2/G3 production authority.

## Route after review

The bounded acceptance-boundary review is complete enough to identify the next decision; it does not certify the whole candidate. No source edit is selected or authorized by this receipt. The next action is a new explicit Owner decision on one bounded R-07 transport-profile reconciliation candidate (or a decision to defer remote transport and preserve only a local fail-closed profile). That task must not attempt to fabricate G1/G2/G3 providers. The Actions support thread continues separately.

## Canonical state

```text
STATIC_REVIEW=M1F_PR531_R01_R08_BOUNDED_REVIEW_COMPLETE
EXHAUSTIVE_LINE_BY_LINE_REVIEW=NOT_CLAIMED
R07_TRANSPORT_PROFILE=INTEGRATION_GAP_IDENTIFIED
PR531=OPEN_DRAFT_UNMERGED
CANDIDATE_HEAD=50cbd2b8b3d643d05726290c76ef13f85731949e
TESTS=NOT_RUN
ACTIONS_USAGE_BLOCK=UNKNOWN
ROOT_CAUSE=UNKNOWN
G1/G2/G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
COMMUNITY_POST=PUBLISHED; DISCUSSION_211346
NEXT_ACTION=OWNER_DECISION_ON_ONE_BOUNDED_R07_TRANSPORT_PROFILE_RECONCILIATION
STOP=NO_SOURCE_EDIT_OR_TEST_EXECUTION_WITHIN_THIS_REVIEW; NO_TRUST_INVENTION; NO_GATE_RELEASE
```

This receipt records a bounded review and a new routing decision. It is not test execution, whole-organ acceptance, positive-read authority, or proof of autonomous algorithmic learning.
