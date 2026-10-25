# Owner decision receipt — one bounded read-only assessment of pre-existing trust assets

- Decision date: 2026-10-25, America/Bogota.
- Decision provenance: explicit current-chat instruction to proceed to the next documented IABV step and use the repository's existing traceability to identify what is still needed to continue the bridge.
- Canonical base verified: `main=65b3fb614e7c4b835af286e7dc357de137f05cb1` after PR #494 was merged and fetched back.
- Authorized task: `M1A_G1_EXISTING_TRUST_ASSETS_BOUNDED_READ_ONLY_ASSESSMENT`.
- Scope: one bounded read-only inventory of pre-existing, source-grounded authority/trust assets and their relevant metadata in the Owner's already-open local Windows/Codex session.

## Why this is next

Live `CURRENT-STATE.md` still records `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED`, independent root/custodian/channel not established, Owner-to-Windows principal not established, authority-to-issuer and issuer-to-exact-server not established, and G1/G2/G3 not established. The previous route's own historical record named this assessment as the next candidate and explicitly required a separate Owner authorization and a supported route. This chat supplies that authorization for the narrow read-only assessment only.

This is an authorization change, not new technical evidence. It does not prove an asset exists or is absent, establish a trust root, or close any gate.

## Scope boundaries

Allowed: inspect relevant existing source/docs to derive exact asset locators; inspect only metadata at those locators; read public certificate/public-key metadata; query metadata for specifically referenced existing services, protected storage and IPC endpoints; compare only redacted identity-match results when a supported route permits. No broad scans.

Prohibited: source edits; tests or test execution; build/runtime/MCP/transport; protected reads; launching or invoking issuer/IPC; reading/exporting private keys or secrets; password/token/cookie/Credential Manager/DPAPI inspection; root/credential enrollment; service/ACL/trust-store/registry changes; TPM preflight repetition; Entra/Authenticator setup repetition; public tunnel, spend, deployment, staging, commit, push, merge or publication.

Codex must preserve the existing candidate's staged/unstaged state and return `SUPPORTED_ROUTE_NOT_FOUND` / `NOT_RUN` if no supported read-only route exists. No fallback route may be used to bypass a denial.

## Required task hand-off

The exact self-contained prompt to be pasted into the already-open Codex session follows.

```text
IA DESTINO = Codex — existing UI/session (the already-open Windows session; do not launch a new app/session).
CAPABILITY REQUIRED = bounded read-only Windows/source provenance inspection of pre-existing trust assets.
WHY THIS AI NOW = the active local candidate and any pre-existing Windows trust/issuer assets are accessible only through the Owner's existing local session; GitHub source review cannot prove local asset existence, custody or ACL state.

TASK = M1A_G1_EXISTING_TRUST_ASSETS_BOUNDED_READ_ONLY_ASSESSMENT
TASK_RESULT_TARGET = EXISTING_TRUST_ASSET_READ_ONLY_ASSESSMENT_ONLY

## Objective

Produce one bounded, read-only evidence inventory of pre-existing assets that could contribute to the IABV G1/G2/G3 trust boundary. Do not build or enable the bridge. Determine whether any genuinely pre-existing, non-circular authority root, Owner-to-Windows-principal binding, protected issuer/process/IPC boundary, or exact-target/same-object mechanism can be evidenced from supported existing artifacts.

## Canonical preflight

1. Refresh live `refs/heads/main` in `https://github.com/jhonf463r/Python.git` and read, in this strict order: `IABV_v1.5/AGENTS.md`; `IABV_v1.5/docs/history/CHAT-ARCH/README.md`; `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md`; `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`; `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`.
2. Confirm the Owner's one-task read-only authorization from the live current route and this task receipt. If the live route or permissions conflict, stop.
3. Verify the actual existing checkout path/repo/branch/HEAD and capture `git status --short` before observation. Preserve all staged and unstaged state. This task is read-only: no snapshots, logs or helper files written into the checkout.
4. Reuse existing source/documentation to identify exact asset locators. Do not repeat the broad 12-path source review; do not substitute public `main` for local checkout state.

## Allowed scope — one task only

- Inspect existing IABV source/configuration/documentation needed to identify exact, already-referenced trust-asset paths, certificate-store selectors, service names or IPC endpoints. Keep source browsing relevant and bounded.
- At only those exact, source-grounded locations, report read-only metadata: whether the asset/entry is present; type; path or store/selector; size and timestamps where relevant; public certificate/key fingerprint and subject where the material is public; file owner/ACL/access-control posture; service registration/account/SID metadata; and named-pipe existence/ACL metadata, if those exact endpoints are already named by existing source/config.
- For a pre-existing private-key container, inspect only metadata/non-exportability/protection status exposed by a supported read-only interface. Do not open, export, sign with, decrypt, dump, or copy the private key.
- Determine whether the source and available metadata establish a non-circular root and custodian/channel; an authenticated relation between the Owner and the relevant Windows principal; a protected issuer-to-server binding; durable anti-replay state; and a versioned resolver that lets the reader consume the exact object authorized.
- Avoid recording personal identifiers in the report. If an identity comparison is required, return only a redacted `MATCH / MISMATCH / UNABLE_TO_COMPARE` result and the evidence type; do not publish usernames, SIDs, tenant/user IDs, key material or other secrets.
- Keep `AUTHORITY_ASSETS=UNKNOWN; NOT_INSPECTED` for any asset not reached through the allowed route. A missing file at one searched path is not global absence.

## Prohibited actions

- No source/document edits, test authoring, test execution, builds, runtime, MCP, real transport or protected reads.
- No invocation of an issuer, no IPC connection that sends a command, no bridge launch, no service start/stop/install, no root or credential creation/enrollment, no signing challenge, no changes to ACLs, registry, trust store, certificates, scheduled tasks or environment.
- Do not inspect or print secrets, private-key bytes, passwords, access/refresh tokens, cookies, browser profiles, Credential Manager contents, DPAPI material or environment-variable values. Do not export any key.
- No broad recursive scan of the user profile, whole drive or certificate stores. Use only existing asset paths/identifiers reached from relevant source/config or a clearly bounded, relevant OS metadata query.
- Do not repeat the closed TPM preflight, recovery-key lookup, EK inspection or certificate-chain experiment. Do not repeat Entra/Authenticator setup.
- No public tunnel, spending, deployment, publication, staging, commit, push, reset, clean, checkout, restore, rebase or merge.
- Do not bypass a denied reader or infer that an unavailable route means assets are absent.

## Evidence contract

Return:
1. `TASK_RESULT=EXISTING_TRUST_ASSET_READ_ONLY_ASSESSMENT_ONLY` or `TASK_RESULT=NOT_RUN; REASON=SUPPORTED_ROUTE_NOT_FOUND` if the route is unavailable.
2. Exact repo/checkout/branch/HEAD and `git status --short` before/after; assert whether the worktree/index are unchanged.
3. A compact table per asset: locator source; metadata observed; custody/independence evidence; trust-boundary relation supported; evidence class (`DIRECT_LOCAL_METADATA`, `SOURCE_STATIC`, `OWNER_REPORTED`, `UNKNOWN`); limitations.
4. For each edge separately: independent root/custodian; Owner-to-Windows principal; authority-to-issuer; issuer-to-exact-server; durable challenge/replay state; G2 policy/revocation; G3 exact target and same-object reader consumption.
5. Exact commands/queries and exit statuses, with output redacted for personal identifiers/secrets. Do not include secrets even if an attempted command reveals them; stop, redact and report the exposure without saving it.
6. A final state classification: `PRESENT_AND_PROVEN_FOR_NARROW_CLAIM`, `PRESENT_BUT_NOT_TRUSTED`, `NOT_FOUND_AT_EXACT_INSPECTED_LOCATOR`, `UNKNOWN_NOT_INSPECTED`, or `SUPPORTED_ROUTE_NOT_FOUND`. Never generalize exact-path nonexistence to global absence.
7. Explicit `TESTS=NOT_RUN`, `BUILD=NOT_RUN`, `RUNTIME=NOT_RUN`, `MCP=NOT_RUN`, `REAL_TRANSPORT=NOT_RUN`, `PROTECTED_READS=FAIL_CLOSED`, and no automatic follow-on.

Stop after this one inventory. Do not implement repairs even if a gap is obvious. Return the evidence for independent reconciliation before another task is selected.
```

## Acceptance and next-state constraints

Accept only a report that provides exact provenance, redacted output, before/after status, per-edge evidence classification and explicit non-execution of all excluded actions. Static/source evidence, asset metadata, public-key fingerprints and successful local authentication are not interchangeable with independent Owner authority.

Maintain fail-closed gates until a later independent reconciliation supports a narrower claim. This task ends after one evidence inventory; it does not automatically authorize source modification or any operational step.