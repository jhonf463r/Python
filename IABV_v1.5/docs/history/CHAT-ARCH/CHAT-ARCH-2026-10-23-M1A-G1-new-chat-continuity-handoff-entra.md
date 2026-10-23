# IABV — New-chat continuity handoff: Entra identity prepared, bridge authority still blocked

- Date: 2026-10-23 (America/Bogota)
- Task: `M1A_G1_NEW_CHAT_CONTINUITY_HANDOFF_ENTRA`
- Project north star: `GOVERNED_IABV_CODEX_BRIDGE`
- Active frontier: `M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY`
- Latest pre-handoff main baseline: `90d4a5f60c9544e7e3a1008f15b11db8aee8f218`
- Operating mode: governed source-grounded coordination; preserve fail-closed behavior; no unapproved spend or runtime activity.

## 1. Mandatory startup protocol for the next chat

At the start of the next chat, do not infer state from memory alone. Revalidate public GitHub `main` first, then retrieve these five routing files in this exact order:

1. `IABV_v1.5/AGENTS.md`
2. `IABV_v1.5/docs/history/CHAT-ARCH/README.md`
3. `IABV_v1.5/docs/history/CHAT-ARCH/CURRENT-STATE.md` — sole current routing authority
4. `IABV_v1.5/docs/history/CHAT-ARCH/CONTEXT-INDEX.md`
5. `IABV_v1.5/docs/history/CHAT-ARCH/MEMORY-OPERATING-PROTOCOL.md`

Then read:
- this handoff;
- the current static assessment [M1A G1 Microsoft Entra no-cost integration — bounded static assessment](./CHAT-ARCH-2026-10-23-M1A-G1-Entra-no-cost-integration-static-assessment.md), blob `025a126f8848cab4ac0e6b33f8bd9f2e4740dda6`;
- [M1A v1.0.1 implementation-prerequisite evidence gate matrix](./CHAT-ARCH-2026-10-22-M1A-v1_0_1-implementation-prerequisite-evidence-gate-matrix.md), blob `1322fdfb26770bcf5bdfab9fd85a7ffcee5d9f37`;
- [M1A v1.0.1 explicit Owner adoption receipt](./CHAT-ARCH-2026-10-22-M1A-v1_0_1-explicit-owner-adoption-receipt.md), blob `34bee2ad8b3b4beeb468e8d563b99f511f0b352d`;
- [Entry 274 consolidated read-decision contract](./CHAT-ARCH-2026-10-13-274-m0b-r8-1-consolidated-read-decision-contract.md).

If any newer canonical override exists on `main`, it supersedes the historical state summarized here. Do not use this file's baseline as the current HEAD after a later commit.

## 2. User intent and operating constraints

The Owner's priority is to unblock IABV with the shortest safe route, maintain the long-running project's continuity, avoid repeated scans and loops, receive complete copy/paste prompts inline, and avoid spending money on subscriptions/apps/resources. The user says the available budget for paid services is zero.

Rules:
- No Azure upgrade to Pay-As-You-Go; do not remove the spending limit; do not purchase Entra P1/P2, Application Proxy, Microsoft 365, or any other paid service.
- Do not deploy Azure VMs, Functions, App Service, databases, gateways, tunnels or other resources for this task.
- Azure subscription/billing/spending-limit state has not been independently verified. Never claim the setup is guaranteed cost-free until that UI state is actually checked.
- Never store tenant ID, user Object ID, email/UPN, QR, access/refresh token, secret, recovery code or private key in a public repository or pasted chat.
- Use the existing directory/user setup; do not create more accounts/directories unless a specifically justified, explicitly authorized need is demonstrated.
- No local checkout, protected data, SQLite, `.env`, credentials, source-runtime probing, or tool invocation by trying alternate paths around a denied route.
- No new app registration, client secret, code changes, test/build/runtime/transport, tunnel launch, merge, deployment or block release without its corresponding explicit bounded authorization.
- Any prompt for another AI must name the target/route, pinned baseline, exact bounded scope, constraints, result schema and stop conditions. Never claim dispatch into the user's Codex UI unless a correlated invocation/result actually occurred.
- The “space-time coordinator” is the user's continuity/coordination metaphor, not evidence of a conscious system, an autonomous runtime agent, or causal learning already proven.

## 3. New Owner-reported progress — preserve provenance

The Owner reports:
- An organizational Microsoft Entra directory exists with an initial `.onmicrosoft.com` domain.
- A dedicated user called `IABV Owner` was created in that directory.
- Microsoft Authenticator was enrolled for that user.
- The user subsequently signed in and completed Authenticator verification successfully.

These are `OWNER_REPORTED`; the coordinator did not independently access the Azure portal or validate an authentication event. Exact directory domain, UPN, tenant ID and user Object ID are deliberately omitted from this public handoff. The project receipt [Owner identity preparation and no-cost route](./CHAT-ARCH-2026-10-23-M1A-G1-owner-identity-preparation-no-cost-route.md), blob `1cbf32702089f12ed0a455a7f7ffc2d160e4a620`, records this privacy boundary.

**Interpretation:** Microsoft Entra ID Free is a plausible no-cost candidate for human Owner authentication. A working MFA login does not make Entra a trusted IABV issuer, grant repository-read authority, prove the Owner-to-Windows-principal binding, or authorize any protected operation. An organizational identity created and administered by the Owner is not automatically an independent authority over IABV. Token issuer/tenant/audience and subject validation, exact server/reader binding, governance acceptance, revocation and authorization remain to be designed and implemented under separate authorization.

## 4. Most important newly grounded source finding

A bounded, static review of exact public GitHub source found:

- `IABV_v1.5/docs/mcp-bridge.md`, blob `e53709d10a7a40d089cc8a55c94a4a23f620718e`, lines 280–282, explicitly states that the HTTP MCP endpoint has no token authentication and warns that any client could invoke tools if the tunnel is public.
- `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`, blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`, lines 134–160, configures disabled DNS-rebinding protection plus wildcard allowed hosts/origins when that SDK security setting exists, for tunnel compatibility.
- The same server source declares transports including `stdio`, `sse` and `streamable-http`; that does not prove which one the real local process currently uses.
- Project metadata `IABV_v1.5/pyproject.toml`, blob `22827c38cc3f7ee3bd3e16f6ed3ec0543841beb1`, does not directly declare an OIDC/JWT validation dependency.
- The public source documents do **not** prove that a tunnel is currently active or that the local process runs the inspected source/configuration. Record `MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED`, not an incident claim.

Safety consequence: do not start or reconnect a public tunnel, or expose the unauthenticated HTTP MCP endpoint, as an experiment. Keep any use local/stdio-only or otherwise non-public until transport-level authentication and distinct operation-level authorization are implemented and independently verified. A transport bearer header by itself would still not satisfy the Entry 274 per-operation decision, scope, revocation, budget, target binding, release and durable receipt requirements.

The full analysis is preserved in [the bounded static assessment](./CHAT-ARCH-2026-10-23-M1A-G1-Entra-no-cost-integration-static-assessment.md). It reviewed public GitHub source and official docs only; no local checkout or runtime was accessed.

## 5. Current gate truth — do not overstate

```text
PRIMARY_OUTCOME=GOVERNED_IABV_CODEX_BRIDGE
ACTIVE_TASK=M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY
LAST_TERMINAL_TASK=M1A_G1_ENTRA_SINGLE_TENANT_AUTH_INTEGRATION_DESIGN_REVIEW
ENTRA_DIRECTORY=OWNER_REPORTED_CREATED
DEDICATED_OWNER_USER=OWNER_REPORTED_CREATED
AUTHENTICATOR_SIGN_IN=OWNER_REPORTED_SUCCESS
IDENTITY_PROVIDER_CANDIDATE=MICROSOFT_ENTRA_ID; NOT_YET_TRUSTED_BY_IABV
TENANT_AND_USER_IDS=NOT_STORED_IN_PUBLIC_REPOSITORY
AZURE_BILLING_STATE=NOT_VERIFIED
COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
MCP_HTTP_TOKEN_AUTH=ABSENT_IN_DOCUMENTED_DESIGN
MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED
DNS_REBINDING_PROTECTION=DISABLED_IN_INSPECTED_CONSTRUCTOR_PATH; EFFECTIVE_RUNTIME_UNVERIFIED
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
ROOT_CUSTODIAN_AND_VERIFICATION_CHANNEL=UNRESOLVED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
BRIDGE=BRIDGE_NOT_READY
TPM_PREFLIGHT_BRANCH=CLOSED_FOR_NOW
COORDINATOR_RUNTIME=NOT_PROVEN
CAUSAL_SPACE_TIME_REUSE=NOT_PROVEN
AUTOMATIC_FOLLOW_ON=FALSE
```

## 6. The eight gates and exact dependency order

The adopted normative design is M1A v1.0.1, blob `7c72474a5f7c114c02320c177d6ea2aea68ad28f`, adopted by the explicit Owner token `ACCEPT_M1A_V1_0_1_SUCCESSOR_BASELINE` for **design only**. Adoption did not close runtime gates.

- **G1:** authenticated Owner/governance principal and trust anchor; exact issuer/reader/server trust chain and Owner-to-Windows binding.
- **G2:** authorized catalogue publisher, producer-class policy, integrity/version lifecycle and authoritative revocation.
- **G3:** versioned server-side operation-to-target resolver tied to real registered call sites.
- **G4:** typed schema/evaluator wired into every protected decision point.
- **G5:** deterministic all-block aggregation, complete active-set attestation and independent per-block releases.
- **G6:** Entry 274 integration: fresh approval, reader verification, target/path binding, budgets, expiry/revocation, race-resistant containment and durable audit/receipts.
- **G7:** separate Owner authorization and execution of the 38 required synthetic conformance cases with correlated evidence.
- **G8:** independent acceptance bound to exact source/test/runtime revisions and honest claim scope.

All eight remain open. Order: evidence route/producer for G1–G3 first; only after authorities exist and a separate implementation authorization, assess G4–G6; then separately authorize G7; independent exact-revision verification for G8. No gate closes by inference from MFA, an Entra tenant ID, a Git hash, design approval, static review or account setup.

## 7. Closed investigations — do not repeat

- Broad Windows bootstrap feasibility.
- GitHub-manifest/TPM-bound issuer design.
- Google OIDC external setup; prior result `NOT_WORTH_EXTERNAL_SETUP`.
- Personal phone/passkey feasibility and general TPM identity pinning. Phone/MFA is relevant human authentication progress but not an IABV trust root.
- TPM preflight/capture: `CLOSED_FOR_NOW`; presence and root cause remain unverified/unresolved. Do not repeat `Get-Tpm`, recovery lookup, EK inspection or chain construction without a new explicit bounded decision.
- The prior M1 scoped-read candidate `ea794a0490fe463e4d13f05e7279ebb3219f34ad` ended `PARTIAL_FAIL_CLOSED_GUARD_ONLY`: reader/list remain denied when no authority can be verified. It is not a working route and not merged/deployed.
- The governance-owned bootstrap design candidate `675c3bdd046de04e4e7d6bb70d616dbce1354e06` remains documentary and conditionally reviewed. It recommends Option D as the only operationally defensible position with current evidence; that option has not been explicitly ratified by the Owner.
- Do not repeat broad tool catalogs, generic feasibility surveys, or reader/list calls. The five IABV tools exposed in Codex are observation/git/read/list tools, not authority issuer/revocation/resolver/release/ledger operations.

## 8. Next bounded step — do not silently auto-implement

The latest design assessment's next action is an Owner decision on a bounded implementation authorization after design. If the Owner authorizes work, the first implementation phase must be isolated and no-cost, beginning with a source-grounded design/implementation plan for:
1. close the public-HTTP endpoint risk before any public tunnel can be used;
2. choose and specify the exact authentication protocol/client flow supported by the installed MCP Python SDK and Codex client;
3. validate access tokens for this API only: exact tenant-specific issuer and tenant ID; trusted signing keys/signature; expiration/not-before; correct audience; authorized subject/object identity; reject ID tokens, wrong-tenant tokens, wrong-audience tokens and missing/unknown claims;
4. separately bind authenticated principal to an interactive, transaction-specific, finite-scope read decision and then bind that decision to the exact live server/workspace identity;
5. require authoritative revocation/freshness, complete applicable-block state, separate block-release authority, a durable correlated intent/result/delivery/persistence receipt and race-resistant reader containment;
6. prove the chosen path stays within zero budget. Do not assume a free identity feature makes all integration services free.
7. only implement after the above design, exact supported client/transport route, and explicit scope/acceptance criteria are approved.

Given the source finding, the immediate security priority is **not** app registration for its own sake. It is confirming an implementation path that can authenticate and authorize the MCP endpoint without public unauthenticated exposure. No route should be exposed just to test authentication.

## 9. Required behavior in the new chat

- Start with the mandatory five-file remote preflight and the current handoff/assessment.
- Give the Owner one concise next action at a time. Do not ask them to revisit account setup unless new evidence shows it failed.
- Present complete copy/paste prompts inline when delegating to Codex. Do not send the Owner to another page solely to copy a prompt.
- Continue no-cost by default. Never ask for private IDs/credentials in chat; if configuration values are necessary later, keep them in local owner-controlled configuration and redact them from public receipts.
- Distinguish `OWNER_REPORTED`, `STATIC_SOURCE_CONFIRMED`, `NOT_VERIFIED`, `NOT_AUTHORIZED`, `INVOKED`, `OBSERVED`, and `CAUSAL_REUSED`.
- Never claim the local server is exposed based only on source; its actual runtime state is unverified.
- Keep protected reads and block releases denied until every authority boundary is proven independently.
- For any GitHub documentation writeback: fetch current main, use repository-root-relative full paths including `IABV_v1.5/`, compare-and-swap, fetch back receipt and all five front doors, compare exact blob hashes, and verify no misplaced files or private identifiers. Do not declare completion before fetch-back.

## 10. Copy/paste starter for the new ChatGPT conversation

```text
Continuemos IABV usando el handoff canónico más reciente de GitHub, no memoria de la conversación solamente.

Repositorio: jhonf463r/Python.
Norte: GOVERNED_IABV_CODEX_BRIDGE.
Frontera activa: M1A_G1_TRUST_BOOTSTRAP_AUTHORITY_BOUNDARY.
Primero revalida main y lee en este orden: IABV_v1.5/AGENTS.md; IABV_v1.5/docs/history/CHAT-ARCH/README.md; CURRENT-STATE.md; CONTEXT-INDEX.md; MEMORY-OPERATING-PROTOCOL.md. Luego lee CHAT-ARCH-2026-10-23-M1A-G1-new-chat-continuity-handoff-entra.md y CHAT-ARCH-2026-10-23-M1A-G1-Entra-no-cost-integration-static-assessment.md. Si main avanzó, respeta el override más reciente.

Nuevo progreso reportado por Owner: creó un directorio Microsoft Entra, usuario IABV Owner y vinculó Authenticator; el inicio de sesión MFA funciona. Trata esto como OWNER_REPORTED. No copies ni solicites UPN, tenant ID, object ID, tokens o secretos en el chat/repositorio público. Azure billing/spending limit no está verificado y el presupuesto para pagos es cero.

Nuevo hallazgo confirmado por revisión estática de fuentes públicas: docs/mcp-bridge.md declara que el endpoint HTTP MCP no tiene autenticación por token y advierte del riesgo si se publica el túnel. server.py deshabilita DNS-rebinding protection y permite wildcard hosts/origins en la ruta de constructor inspeccionada. La exposición local real no está verificada; no iniciar/reconectar túnel público ni alegar incidente activo. No hay evidencia de middleware OIDC/JWT en la ruta inspeccionada. Entra es proveedor candidato de autenticación humana, no autoridad de lectura IABV.

Conservar: M1A v1.0.1 adoptado solo como diseño; G1/G2/G3 no establecidos; 8 gates abiertos; GOVENANCE=KEEP_BLOCKED; READ_LIST=FAIL_CLOSED; BRIDGE=BRIDGE_NOT_READY; tests/build/runtime/transport no ejecutados. No repetir la investigación general Windows/TPM, Google OIDC, passkeys, herramientas o bootstrap ya cerrada.

Siguiente paso: presentar la decisión explícita para autorizar —o no— una implementación aislada de coste cero. Antes de cualquier código, fijar una ruta compatible con MCP/Codex, resolver la falta de autenticación del endpoint y diseñar validación de access tokens tenant/issuer/audience/claims más autorización por operación, revocación, vínculo a servidor exacto, liberación independiente y recibos durables. No registrar app, crear secretos, contratar servicios, tocar producto, ejecutar tests/runtime ni abrir bloqueos hasta autorización específica. Mantener todo trabajo reversible y documentado, con prompts completos inline y sin repetir pasos ya ejecutados.
```
