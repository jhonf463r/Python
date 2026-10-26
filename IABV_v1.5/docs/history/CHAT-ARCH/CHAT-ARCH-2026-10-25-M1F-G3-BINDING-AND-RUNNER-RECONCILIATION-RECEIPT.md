# M1F follow-up — G3 identity-binding correction and hosted runner reconciliation

- Receipt ID: IABV_M1F_G3_BINDING_AND_RUNNER_RECONCILIATION_2026-10-25
- Observed at: 2026-10-25 21:15 America/Bogota (2026-10-26 UTC).
- Live main: 24a08f9fc4c82ee261f21d95707bcbd5d86f0d36.
- Candidate PR: https://github.com/jhonf463r/Python/pull/531 — open draft, not merged.
- Candidate branch: codex/iabv-m1f-authz-candidate-review-20261025.
- Candidate head after bounded source corrections: 50cbd2b8b3d643d05726290c76ef13f85731949e.
- The PR base remains 7ddfe285b1a3267f9ef6f57f862cca78bc8438c2, one documentation-only commit behind current main. The latest main commit is documentation-only and does not modify candidate product files.

## 1. New source findings and bounded corrections

### G3 resolved-target identity must match the opened capability

Static review found that the coordinator required the target resolver to return the identical opened-target object and matching target/root/policy binding IDs, but did not compare all three contextual identity fields against the opened capability itself. A resolver result could therefore agree with the host request while carrying workspace metadata different from the handle-root capability.

Candidate correction:
- ReadAuthorizationCoordinator.authorize now requires target.workspace_id, target.checkout_id and target.resolver_version to equal those same fields on opened_target.
- The MCP enforcement guard independently requires the issued permit's workspace_id, checkout_id and resolver_version to equal the opened target's fields.
- Six parameterized regression cases were added: three resolver-to-capability mismatches and three permit-to-capability mismatches.

Fetch-back blob IDs at the candidate head:
- IABV_v1.5/src/iabv_v15/services/security/read_authorization.py: 3a57d1148c175040b7b747a6e04411c542c51dd3.
- IABV_v1.5/src/iabv_v15/infra/mcp/server.py: af0d95dd27172685a04e28f51d8bdc97c4f00b32.
- IABV_v1.5/tests/test_read_authorization.py: e796237ae4d1743e893ceced93e07213ca2354d0.

The regression tests use the existing synthetic CNG-backed signature chain on Windows. They do not replace cryptographic verification with an unconditional successful result. The test code was fetched back and the source change inspected statically.

### Bridge startup must require the approved workspace-root provider

A second source gap was found in MCPBridgeService._authorization_organ_gate_block(): it checked that the authorization coordinator existed and its listed dependencies were present, but did not check the separate approved_workspace_root_provider required by protected-read composition.

Candidate correction:
- Startup now blocks with APPROVED_WORKSPACE_ROOT_PROVIDER_UNAVAILABLE when the provider is absent.
- Startup blocks with APPROVED_WORKSPACE_ROOT_PROVIDER_INVALID when current_workspace_root is not callable.
- Tests cover absent and malformed providers and assert neither the MCP server runner nor tunnel runner starts.
- The presence-only test fixture never supplies an approved root and is not evidence of root authority.

Fetch-back blob IDs:
- IABV_v1.5/src/iabv_v15/services/evolution/mcp_bridge_service.py: 7df470fa852c8f9a2adf7d27a133b5b50cd6d1d3.
- IABV_v1.5/tests/test_mcp_bridge_service.py: 50d3b69732a44fe642f6015d851b770e54d9372c.

These are source-level corrections in the isolated candidate. They do not provision a root, authenticate a provider, or establish G3 native semantics.

## 2. Execution attempts and verified outcome

### Windows candidate workflows

- Run 40258140268: https://github.com/jhonf463r/Python/actions/runs/40258140268.
- Run 40258135717: https://github.com/jhonf463r/Python/actions/runs/40258135717.

For both, the GitHub Jobs API reports labels [windows-latest], runner_id=0, empty runner_name, and steps=[]. They terminated before checkout, dependency installation or pytest.

### Separate Ubuntu fallback

A separate validation branch was created from the exact then-current candidate source plus a read-only, no-secret Linux test workflow. The initial workflow definition was corrected so runner-scoped temporary data is set inside a step. The valid fallback run is:

- Run 40257696172: https://github.com/jhonf463r/Python/actions/runs/40257696172.
- Job label: ubuntu-latest.
- Jobs API: runner_id=0, empty runner_name, steps=[].

This independent attempt also ended before the first step. It establishes that the blocker is not limited to the Windows runner label. The precise GitHub Actions assignment/root cause remains unverified; no source assertion has been shown to fail.

The tool execution container also failed to resolve github.com for a local Git clone. Consequently:
- TESTS=NOT_RUN.
- BUILD=NOT_RUN.
- RUNTIME=NOT_RUN.
- NATIVE_WINDOWS_HANDLES_AND_ACL=NOT_RUN.
- AUTHENTICATED_IPC_AND_ROLLBACK_PROTECTION=NOT_RUN.
- REAL_MCP_TRANSPORT_AND_PROTECTED_READS=NOT_RUN.

The source corrections and test definitions are not a substitute for executed results.

## 3. Production authority inventory — evidence boundary

Direct fetch-back of AppBootstrap on main contains no approved_workspace_root_provider wiring. The candidate AppBootstrap still registers ReadAuthorizationCoordinator.unconfigured() and does not wire a production approved-root provider. Fetching .github/iabv-g1-bootstrap-manifest.json returned 404 on both main and the candidate ref. This is a repository-content observation only; it does not prove that no local or external trust material exists.

Therefore:
- AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED.
- G1 independent trust root and authenticated Owner/governance principal: NOT_ESTABLISHED.
- G2 trusted production policy/revocation provider: NOT_ESTABLISHED.
- G3 production resolver, approved root and native same-object semantics: NOT_ESTABLISHED.
- Production authenticated issuer IPC, host-owned process identity and anti-rollback replay remain unestablished.

No key, manifest, provider, identity or authority was fabricated.

## 4. Canonical disposition

```text
MAIN=24a08f9fc4c82ee261f21d95707bcbd5d86f0d36
CANDIDATE_PR=531; OPEN_DRAFT; MERGED=FALSE
CANDIDATE_HEAD=50cbd2b8b3d643d05726290c76ef13f85731949e
G3_IDENTITY_BINDING_SOURCE_FIX=FETCHBACK_VERIFIED; STATIC_ONLY
APPROVED_ROOT_STARTUP_PREFLIGHT=PATCHED; STATIC_ONLY
FOCUSED_REGRESSION_CASES=AUTHORED; TESTS=NOT_RUN
WINDOWS_ACTIONS=FAILED_BEFORE_FIRST_STEP; RUNNER_ID=0
UBUNTU_ACTIONS=FAILED_BEFORE_FIRST_STEP; RUNNER_ID=0
HOSTED_RUNNER_ROOT_CAUSE=NOT_VERIFIED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
WHOLE_ORGAN_ACCEPTANCE=NOT_GRANTED
AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED
PROTECTED_READS=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
```

## 5. Next action and stop conditions

The candidate has received two bounded, source-correctable hardening changes discovered during the current review. Do not continue a speculative patch loop in the absence of execution evidence or a newly evidenced defect.

Next action: when an approved execution backend actually assigns a runner, run the three focused suites against the then-current exact PR #531 head, capture full logs and reconcile every result. The runner assignment signal must be a nonzero runner_id, a nonempty runner_name, and actual step records; a completed failure with steps=[] is not test evidence.

Then continue the separate trust-boundary evidence process for G1/G2/G3, Windows-native containment and the remaining canonical gates. Do not merge PR #531, enable protected reads, start production transport, or infer whole-organ acceptance from static checks or Git blob identity.
