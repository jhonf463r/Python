# MCP Bridge — IABV v1.5 (fail-closed implementation tranche)

## Operational status

The bridge is **not ready for governed/protected operations**. G1/G2/G3 remain unestablished. This tranche prepares tenant-pinned Entra access-token validation and prevents unconfigured or non-loopback transports from starting. It does not create an Entra application, approve a canonical URL, perform Owner enrollment, or authorize protected repository reads.

- Target SDK: `mcp==1.30.0`.
- Target transport: Streamable HTTP only.
- Bind: `127.0.0.1:8000` only.
- SSE and stdio are rejected until their own authorization boundary is implemented and verified.
- Public Cloudflare tunnels are disabled in both the script launcher and the application bridge runner.
- Repository content reads and directory listings return `scoped_read_authority_unavailable` until a verified scoped-read authority is wired.

## Required local configuration

The HTTP server refuses to start when configuration is absent, partial, malformed, or inconsistent. These environment variables are required together:

| Variable | Purpose |
|---|---|
| `IABV_ENTRA_TENANT_ID` | Exact Entra tenant GUID. |
| `IABV_ENTRA_API_CLIENT_ID` | API application/client GUID; this is the expected Entra v2 token `aud`. |
| `IABV_ENTRA_OWNER_OBJECT_ID` | Immutable Entra object ID of the Owner. |
| `IABV_ENTRA_REQUIRED_APP_ROLE` | Exact app role required for the API. |
| `IABV_ENTRA_ALLOWED_CLIENT_IDS` | Comma-separated allowlist of client application GUIDs. |
| `IABV_ENTRA_APPLICATION_ID_URI` | Approved Application ID URI for the MCP resource. |
| `IABV_MCP_RESOURCE_SERVER_URL` | Approved canonical HTTPS resource URL; must exactly equal the Application ID URI. |

No real values or secrets belong in source control, issues, logs, or chat transcripts. The canonical HTTPS URL, tenant/application values, client allowlist, Owner mandate, and role assignments are not established by this code change. Do not invent values to satisfy the preflight.

## Validation contract

The verifier obtains OpenID metadata from the tenant-pinned Entra v2 endpoint, checks that the returned issuer exactly matches the configured issuer, restricts the JWKS endpoint to HTTPS on `login.microsoftonline.com`, rejects redirects, caches signing keys for a bounded interval, and refreshes once when a key ID is unknown. It accepts only RS256 signatures and validates signature, issuer, tenant, expiry/not-before/issued-at, token version, exact GUID `aud`, Owner `oid`, allowed `azp`/`appid`, and the required `roles` entry. Verification errors are denied without logging token material.

The Application ID URI/resource URL and the token `aud` are separate values and are checked separately. SDK `validate_token_resource` is explicitly disabled because Entra v2 `aud` is the API client GUID rather than the URL; the verifier still validates that GUID strictly. MCP SDK authorization metadata and HTTP challenges are provided by the pinned SDK when the configured auth settings are present.

A valid token proves neither G1 nor permission to read repository contents. The verifier is authentication/role input only. The existing independent G1/G2/G3 and per-operation scoped-read gates remain required.

## Local launch

Use `scripts/run_mcp_bridge.ps1` only from an isolated reviewed checkout when an additional launch authorization exists. The script enforces Streamable HTTP, `127.0.0.1:8000`, and no tunnel. It launches the server in the foreground and does not call `cloudflared`. The server refuses to start unless the full configuration above is valid. This documentation change does not authorize running it.

Do not use `scripts/start_iabv.ps1` as an implementation/test harness: that wrapper has additional synchronization/startup behavior and is not needed for this source-only phase.

## Acceptance tests planned (not run in this phase)

- Empty configuration returns no auth config; partial or mismatched configuration fails closed.
- Valid signature with correct tenant, API audience, Owner object ID, allowed client, and required role is accepted by the verifier.
- Invalid signature, unknown key, redirect/JWKS failure, wrong issuer/tenant/audience/Owner/client/role, missing claims, expired token, ID token, or Graph token is rejected.
- HTTP startup without complete Entra configuration fails before listening; SSE and stdio are rejected.
- Loopback bind stays fixed and host/origin wildcard configuration is not introduced.
- `read_repo_file` and `list_repo_directory` do not open or enumerate paths without a verified scoped-read authority.
- Production Cloudflare tunnel runner does not start a child process.

TESTS=NOT_RUN
BUILD=NOT_RUN
RUNTIME=NOT_RUN
PROTECTED_READS=FAIL_CLOSED
OPTION_D=UNCHANGED
BRIDGE=BRIDGE_NOT_READY
AUTOMATIC_FOLLOW_ON=FALSE
