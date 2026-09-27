# BIO-META-03ZK-R4.4-I.1 — Devin Credential Inventory Evidence

## Provenance

- **Repository**: jhonf463r/Python
- **Subdirectory**: IABV_v1.5/
- **Branch**: devin/bio-meta-03n-controlmaster-external-path
- **HEAD**: a807429baecea810fc06c6d1929ba407eeced4be
- **Parent**: 25906befa32c422d10e74cb9c5fe373ac86ff958

## Runtime Evidence

- **Timestamp UTC**: 2026-09-27T00:59:07.949698+00:00
- **Python**: 3.14.4 (tags/v3.14.4:23116f9, Apr 7 2026, 14:10:54) [MSC v.1944 64 bit (AMD64)]
- **Working tree**: Clean (no source changes, only __pycache__ and test artifacts)

## Credential Loading

- **_auto_load_secrets() executed**: YES
- **_resolve_devin_api_key() executed**: YES
- **Resolved credential present**: YES
- **Resolved credential length**: 153 characters

### Environment Variables

- **DEVIN_API_KEY_IABV**: MISSING
- **IABV_DEVIN_API_KEY**: MISSING
- **DEVIN_API_KEY**: PRESENT

## API Probe Results

### Read-Only Probe (GET)

- **Endpoint**: GET https://api.devin.ai/v1/sessions?limit=1
- **HTTP Status**: 200
- **Call success**: YES
- **Authentication**: Successful

### Quota Probe (POST)

- **Endpoint**: POST https://api.devin.ai/v1/sessions
- **HTTP Status**: 403
- **Error classification**: out_of_quota
- **Error type**: billing/quota restriction
- **Detail**: "Your organization has a billing error. Error: out_of_quota"

## Credential Inventory

### Secrets File

- **File**: ~/.iabv_secrets.ps1
- **Exists**: YES
- **VARIABLE_ENTRY_COUNT**: 1

### Credential Details

- **Variable**: DEVIN_API_KEY
- **Present**: YES
- **Length**: 153 characters
- **Type**: apk_user_* (user API key)
- **Structure**: base64-encoded user:organization identifier
- **Unique credential count**: 1
- **Duplicates detected**: NO

## IABV Capacity

### Resolution Strategy

- **Variables searched**: 3 (DEVIN_API_KEY_IABV, IABV_DEVIN_API_KEY, DEVIN_API_KEY)
- **Strategy**: Fallback (first available wins)
- **Multi-credential support**: NO
- **Current selection**: DEVIN_API_KEY (only available)

## Maximum Valid Claim

The evidence demonstrates that:

1. IABV has exactly **ONE Devin credential** configured in its secrets file
2. The credential is of type `apk_user_*` (user API key)
3. The credential **authenticates successfully** with the Devin API (HTTP 200 on GET)
4. The credential is **blocked by organization quota** (HTTP 403, out_of_quota)
5. IABV currently uses a **simple fallback strategy** and does not support multi-credential selection
6. The blockage is at the **organization billing/quota level**, not at the credential or technical level

## States

- **RUNTIME_PROBE_EXECUTED**: YES
- **CREDENTIAL_INVENTORY_OBSERVED**: YES
- **GET_200_OBSERVED**: YES
- **POST_403_OBSERVED**: YES
- **OUT_OF_QUOTA_OBSERVED**: YES
- **SANITIZED_ARTIFACT_CREATED**: YES
- **ARTIFACT_COMMITTED**: (pending)
- **REMOTE_READBACK_CONFIRMED**: (pending)
- **SECRETS_EXPOSED**: NO

## Next Steps

The current limitation is **organization-level quota**, not a technical limitation of IABV's credential resolution. Once the organization's quota/billing issue is resolved, the existing credential should allow real Devin session creation without architectural changes.

The evidence does **NOT** support implementing multi-credential selection, as only ONE credential exists in the environment.
