# BIO-META-03ZK-R4.4-J — READ-ONLY Diagnostic of Devin Blockage

## Provenance

- **Repository**: jhonf463r/Python
- **Subdirectory**: IABV_v1.5/
- **Branch**: devin/bio-meta-03n-controlmaster-external-path
- **HEAD**: 2445e874a0320eb9cbcaa580560f27cc07c1cf15
- **Parent**: e2b6cddf1c9378c35e8b0d2ceea55fa02eb86bd3

## Code Inspection

### DevinApiToolAdapter (tool_adapters.py)

**Location**: `src/iabv_v15/services/tools/tool_adapters.py` (lines 1813-2099)

**Base URL**: `https://api.devin.ai/v1`

**Endpoints used**:
- `POST /v1/sessions` → create session
- `GET /v1/sessions?limit=1` → availability check (is_available)
- `GET /v1/session/{id}` → poll session status

**Authentication**:
- Header: `Authorization: Bearer {api_key}`
- `org_id` parameter: kept for backwards compatibility, unused in v1 API
- API key resolution: via `_resolve_devin_api_key()` from bootstrap

**Error handling**:
- 401: Not explicitly handled (treated as general failure)
- 403: Treated as general HTTP error, error message returned to caller
- Out of quota: No specific handling, just HTTP status code captured

**READ-ONLY check**:
- `is_available()` uses `GET /v1/sessions?limit=1` to verify credential
- No other READ-ONLY endpoints for quota/organization/billing are called

**Documentation citation from code**:
> Endpoints reales de la API (v1):
>   POST https://api.devin.ai/v1/sessions        -> crear sesion
>   GET  https://api.devin.ai/v1/session/{id}    -> poll estado
>
> El Bearer token identifica la organizacion; ``org_id`` se conserva
> solo por compatibilidad con el constructor previo pero no se usa en
> las llamadas reales.

## Official Documentation Review

### v1 API Status

**Source**: https://docs.devin.ai/api-reference/v1/overview

**Status**: **DEPRECATED**

> This API version is deprecated. Use API v3 with service user authentication. See the migration guide for step-by-step instructions.

**Authentication**:
- v1/v2: API keys (starts with `apk_user_` or `apk_`)
- v3 (current): Service user tokens (starts with `cog_`)

**Scoping**:
- v1: Organization-scoped `(org_id, user_id)` pair
- v1: No RBAC permission system (all-or-nothing by key scope)
- v3: Role-based with granular permissions

### Migration Guide

**Source**: https://docs.devin.ai/api-reference/getting-started/migration-guide

**Comparison**:

| Area | v1/v2 (Legacy) | Current API |
| --- | --- | --- |
| Authentication | API keys (starts with `apk_user_` or `apk_`) | Service user tokens (starts with `cog_`) |
| Base URL | `/v1/*`, `/v2/*` | `/v3/organizations/*`, `/v3/enterprise/*` |
| Permissions | Key-level (all or nothing) | Role-based with granular permissions |

**Endpoint mapping**:
- Create session: `POST /v1/sessions` → `POST /v3/organizations/{org_id}/sessions`
- List sessions: `GET /v1/sessions` → `GET /v3/organizations/{org_id}/sessions`

### READ-ONLY Endpoints for Quota/Organization

**Enterprise API** (https://docs.devin.ai/desktop/accounts/api-reference/api-introduction):
- Requires service key authentication (not personal API key)
- Available for Enterprise plans only
- Endpoints: `/Analytics`, `/GetUsageConfig`, `/GetTeamCreditBalance`
- Requires permissions: Analytics Read, Billing Read
- Base URL: `https://server.codeium.com/api/v1/` (not api.devin.ai)

**v3 ACU Limits** (https://docs.devin.ai/api-reference/v3/acu-limits/get-devin-acu-limits):
- Endpoint: `GET /v3/enterprise/consumption/acu-limits/devin`
- Requires service user with `ManageBilling` permission at enterprise level
- Not accessible with v1 API keys

**Conclusion**: No READ-ONLY endpoints exist in v1 API to query quota, billing, or organization status. All quota/billing endpoints require v3 + service user + enterprise permissions.

## Current Credential Analysis

**Type**: `apk_user_*` (user API key)

**Format**: Base64-encoded `user_id:org_id` identifier

**Classification**: v1/v2 legacy credential (from migration guide)

**Capabilities**:
- Can authenticate with v1 API (proven by GET /v1/sessions?limit=1 → 200)
- Cannot access v3 endpoints (credential type mismatch)
- Cannot access Enterprise API (requires service key, not personal API key)
- Cannot query quota/billing (no v1 endpoints for this)

## Hypothesis Evaluation

### H1: Organization quota exhausted
- **Evidence for**: Prior POST /v1/sessions returned 403 with "out_of_quota" message
- **Evidence against**: No independent READ-ONLY verification possible with current credential
- **Status**: POSSIBLE (prior self-reported, cannot verify independently)

### H2: Billing restriction
- **Evidence for**: "out_of_quota" message suggests billing/quota issue
- **Evidence against**: No independent verification possible with current credential
- **Status**: POSSIBLE (related to H1)

### H3: Permission restriction
- **Evidence for**: v1 API has no granular RBAC (all-or-nothing by key scope)
- **Evidence against**: GET /v1/sessions works (authentication succeeds)
- **Status**: REFUTED (if permission were denied, GET would also fail)

### H4: Credential type restriction
- **Evidence for**: v1 API is deprecated; current credential is v1 type
- **Evidence against**: GET /v1/sessions works with v1 credential
- **Status**: NOT_PROVEN (v1 still works for GET, unknown for POST)

### H5: Legacy endpoint restriction
- **Evidence for**: v1 is deprecated; migration to v3 recommended
- **Evidence against**: Documentation states v1 "will continue to work during deprecation period"
- **Status**: POSSIBLE (deprecation may affect certain operations)

### H6: v1 + credential type combination
- **Evidence for**: v1 deprecated + apk_user_* = legacy credential
- **Evidence against**: No specific evidence that this combination blocks POST
- **Status**: POSSIBLE (plausible but unproven)

## Diagnostic Matrix

| Hypothesis | Evidence For | Evidence Against | Status |
|------------|--------------|------------------|--------|
| Organization quota exhausted | Prior 403 out_of_quota | No independent verification | POSSIBLE |
| Billing restriction | out_of_quota message | No independent verification | POSSIBLE |
| Permission restriction | v1 has no RBAC | GET succeeds (auth works) | REFUTED |
| Credential type restriction | v1 deprecated | GET works with v1 credential | NOT_PROVEN |
| Legacy endpoint restriction | v1 deprecated | v1 still works during deprecation | POSSIBLE |
| v1 + credential type combination | v1 + apk_user_* = legacy | No specific evidence | POSSIBLE |

## Maximum Valid Claim

Based on code inspection and official documentation:

1. **V1 API STATUS**: DEPRECATED but still functional during deprecation period
2. **CREDENTIAL TYPE**: `apk_user_*` is a v1/v2 legacy personal API key
3. **AUTHENTICATION**: Succeeds for GET operations (proven by independent verification)
4. **READ-ONLY ENDPOINTS**: No v1 endpoints exist to query quota, billing, or organization status
5. **QUOTA VERIFICATION**: Cannot be independently verified with current credential (requires v3 + service user + enterprise permissions)
6. **PRIOR 403**: Previous POST /v1/sessions returned 403 with "out_of_quota" (self-reported, not independently verified)
7. **ROOT CAUSE**: NOT_PROVEN - Cannot be distinguished between quota, billing, or deprecation-related restrictions without READ-ONLY access

## Limitations

- No READ-ONLY endpoints available in v1 API for quota/billing/organization diagnosis
- Enterprise API requires service key (not current personal API key)
- v3 endpoints require service user token (not current v1 credential)
- Independent verification of the 403 cause is not possible with current setup

## Conclusion

**ROOT_CAUSE_NOT_PROVEN**

The blockage cannot be definitively diagnosed without either:
1. A v3 service user token with ManageBilling permissions to query ACU limits
2. Access to Enterprise API with service key and Billing Read permissions
3. Devin support/admin to provide organization quota/billing status

The current credential (v1 personal API key) provides:
- Authentication: YES (GET /v1/sessions works)
- Quota/billing read access: NO (no such endpoints in v1)
- Independent diagnosis capability: NO

## Next Steps

To determine the root cause definitively, one of the following would be required:
1. Obtain a v3 service user token with ManageBilling permissions
2. Contact Devin support for organization quota/billing status
3. Migrate to v3 API with service user authentication (per migration guide)

No architectural changes to IABV can resolve this without additional diagnostic access.
