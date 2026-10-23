# M1A G1 — Microsoft Entra no-cost integration: bounded static assessment

- Date: 2026-10-23 (America/Bogota).
- Task: `M1A_G1_ENTRA_SINGLE_TENANT_AUTH_INTEGRATION_DESIGN_REVIEW`.
- Review mode: bounded static review of public GitHub source and official Microsoft documentation; no runtime or local checkout access.
- Current source snapshot: `main` at `661297b10445d8fcd3bcc59716c209cf728d343a`.
- Owner progress provenance: Owner-reported Entra directory, dedicated IABV Owner user, Authenticator enrollment and successful sign-in. Exact tenant/user identifiers intentionally omitted from public history.

## 1. Decision summary

**Disposition: `NO_COST_IDENTITY_AUTHENTICATION_IS_PLAUSIBLE; IABV_AUTHORITY_AND_MCP_ENDPOINT_PROTECTION_NOT_IMPLEMENTED`.**

The new Entra identity is a viable candidate for authenticating the human Owner through a single-tenant Microsoft identity flow, subject to exact tenant/issuer/audience validation. Microsoft Entra ID Free documents MFA with Microsoft Authenticator via security defaults; Conditional Access and Application Proxy are premium/licensed features and are excluded from this no-cost route. References:
- https://learn.microsoft.com/en-us/entra/fundamentals/licensing
- https://learn.microsoft.com/en-us/entra/identity/platform/single-and-multi-tenant-apps
- https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens
- https://learn.microsoft.com/en-us/entra/identity-platform/how-to-add-redirect-uri

This is not proof that Azure billing safeguards are enabled, nor that an application registration, OAuth flow, or IABV integration exists.

## 2. Source findings on the current MCP route

Public source reviewed:
- `IABV_v1.5/docs/mcp-bridge.md`, blob `e53709d10a7a40d089cc8a55c94a4a23f620718e`, lines 280–282.
- `IABV_v1.5/src/iabv_v15/infra/mcp/server.py`, blob `17b87a1555a63a6350b7f2f02e8f8ec61ad24f7c`, lines 134–160 and 3172–3201.
- `IABV_v1.5/pyproject.toml`, blob `22827c38cc3f7ee3bd3e16f6ed3ec0543841beb1`.

Findings:
1. The bridge document explicitly states that the MCP endpoint has no token authentication and that any client could invoke tools if the tunnel is public; it recommends adding authentication before production.
2. In the inspected FastMCP constructor, when the SDK exposes `TransportSecuritySettings`, DNS-rebinding protection is disabled and host/origin allowlists are set to `*` to support the tunnel. This is not authentication. Whether the local running process uses this exact source/configuration is unverified.
3. The project-level dependency list does not directly declare an OIDC/JWT validation library. MCP and Uvicorn are separately installed per the bridge guide without a version pin in that project file. This makes the exact auth integration and client compatibility a design question; no middleware or authorization changes were made.
4. No evidence in this bounded review shows the MCP endpoint currently running or exposed publicly. Do not infer an active exposure incident from the source documentation alone.

**Safety requirement:** do not expose the current unauthenticated HTTP MCP endpoint through a public tunnel. Until authentication and authorization are implemented and independently tested, preserve local/stdio-only or otherwise non-public use; do not launch or reconnect a public tunnel as a test.

## 3. Minimum design for an Entra-based candidate

Before registering an application or editing code, the design must pin:
- exact single-tenant directory and the tenant identifier, kept in owner-controlled configuration rather than public chat/repository;
- tenant-specific OpenID Connect metadata and signing-key retrieval;
- exact issuer (`iss`) and tenant (`tid`) validation, signature, expiry/not-before, audience (`aud`), authorized subject/object identity (`oid`/`sub`) and client/actor claims as appropriate;
- token type and flow: the MCP API validates access tokens issued for that API, not generic ID tokens or tokens for another resource;
- the intended MCP client/authorization protocol and callback/redirect URI, if required by that flow;
- no credentials or client secrets committed to the repository, and no paid resource deployment.

The Microsoft identity platform explicitly requires validating the audience, tenant and subject/actor, and access tokens must be validated by the API for which they were issued. A signed token or successful MFA is authentication evidence, not permission for a repository read.

## 4. Remaining IABV authority requirements

Entra authentication alone does not implement or prove:
- the governed Owner-to-Windows-principal bootstrap binding;
- binding of the trusted issuer credential to the exact running IABV server instance and source revision;
- an operation-to-target resolver;
- trusted versioned catalogue, producer allowlist and authoritative revocation;
- fresh, operation- and path-scoped decisions consumed by the reader before each operation;
- complete all-block aggregation and separate independent release authority;
- durable correlated intent/result/delivery/persistence receipts and later causal reuse.

Therefore `G1`, `G2`, and `G3` remain `NOT_ESTABLISHED`; all eight implementation prerequisites remain open; protected reads and block releases remain denied.

## 5. Cost boundary

The proposed design should require only Entra ID Free authentication configuration and code that runs in the existing local IABV environment; this is a design target, not a verified billing guarantee. No Azure subscription billing state, spending limit, or resource inventory was inspected. Do not remove the spending limit, upgrade to Pay-As-You-Go, deploy App Service/VM/Function/other billable Azure resources, purchase P1/P2, or enable Application Proxy. Standard app registration has not been performed in this task. The actual selected flow may have requirements that need further review before any setup.

## 6. Canonical decision

```text
TASK=M1A_G1_ENTRA_SINGLE_TENANT_AUTH_INTEGRATION_DESIGN_REVIEW
REVIEW=BOUNDED_STATIC_PUBLIC_SOURCE_AND_OFFICIAL_DOCS
ENTRA_IDENTITY_PROVIDER_CANDIDATE=PLAUSIBLE_FOR_OWNER_AUTHENTICATION
ENTRA_TRUSTED_BY_IABV=NO
MCP_HTTP_TOKEN_AUTH=ABSENT_IN_DOCUMENTED_DESIGN
MCP_PUBLIC_TUNNEL_ACTIVE=UNVERIFIED
DNS_REBINDING_PROTECTION=DISABLED_IN_INSPECTED_CONSTRUCTOR_PATH; EFFECTIVE_RUNTIME_UNVERIFIED
ACCESS_TOKEN_VALIDATION=NOT_IMPLEMENTED_OR_NOT_ESTABLISHED_IN_INSPECTED_PATH
OWNER_TO_WINDOWS_PRINCIPAL=NOT_ESTABLISHED
ISSUER_TO_EXACT_SERVER=NOT_ESTABLISHED
G1=NOT_ESTABLISHED
G2=NOT_ESTABLISHED
G3_VERSIONED_TARGET_RESOLVER=NOT_ESTABLISHED
IMPLEMENTATION_PREREQUISITES=8; CLOSED=0
IMPLEMENTATION=NOT_AUTHORIZED
TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
REAL_TRANSPORT=NOT_RUN
AZURE_BILLING_STATE=NOT_VERIFIED
COST_POLICY=NO_PAID_SERVICES; NO_RESOURCE_DEPLOYMENT
GOVERNANCE=KEEP_BLOCKED
READ_LIST=FAIL_CLOSED
BRIDGE=BRIDGE_NOT_READY
NEXT_ACTION=OWNER_DECISION_ON_BOUNDED_IMPLEMENTATION_AUTHORIZATION_AFTER_DESIGN
```

This assessment authorizes no application registration, client secret, source mutation, test, build, runtime, transport, tunnel launch, merge, deployment or operational unblock.
