# BIO-META-03ZK-R4.4-L — Credential Inventory / Identity Gap Audit

## Provenance

- **Repository**: jhonf463r/Python
- **Subdirectory**: IABV_v1.5/
- **Branch**: devin/bio-meta-03n-controlmaster-external-path
- **HEAD**: 47b4c4189192cd832d85bd4962c47b62bef733ae
- **Parent**: 2445e874a0320eb9cbcaa580560f27cc07c1cf15

## A. DISCOVERY — Where Devin Credentials Can Exist

### Current Sources (Inspected)

**1. ~/.iabv_secrets.ps1**
- **Location**: User home directory
- **Format**: PowerShell script with `$env:NAME = 'value'` assignments
- **Loading**: `_auto_load_secrets()` in bootstrap.py
- **Injection**: Loads into `os.environ` if not already set
- **Persistence**: Written by `save_secret_to_profile()` in auto_correction_engine.py
- **Current Devin entry**: 1 (DEVIN_API_KEY)

**2. Environment Variables**
- **Resolution order**: `_DEVIN_API_KEY_ENV_VARS` = ('DEVIN_API_KEY_IABV', 'IABV_DEVIN_API_KEY', 'DEVIN_API_KEY')
- **Resolver**: `_resolve_devin_api_key()` returns first non-empty value
- **Current behavior**: Single-credential fallback (first available wins)

**3. SecretVault / CredentialBroker**
- **Location**: `services/security/credential_broker.py`, `services/capture/secret_vault.py`
- **Backend**: keyring (optional runtime dependency)
- **Model**: `SecretReference` with domain, account, field_role, key, created_at_utc, available
- **Usage**: Currently used for other providers (GitHub, etc.) but NOT for Devin
- **Current Devin integration**: NONE (Devin uses secrets.ps1, not SecretVault)

**4. Configuration Files**
- **Inspected**: No additional credential configuration files found
- **UI-managed secrets**: CredentialBroker can request credentials via UI prompts
- **Test fixtures**: No Devin-specific credential fixtures found in tests

### Summary of Discovery

| Source | Devin Usage | Metadata Stored | Multi-Credential Support |
|--------|--------------|----------------|------------------------|
| ~/.iabv_secrets.ps1 | YES (primary) | NO (raw values only) | NO (no identity/distinguishing metadata) |
| Environment Variables | YES (via resolver) | NO (raw values only) | NO (fallback, no selection) |
| SecretVault / CredentialBroker | NO (not used for Devin) | YES (domain, account, field_role, created_at_utc) | YES (supports multiple accounts per domain) |

## B. IDENTITY — Metadata Currently Available

### CredentialRecord (CredentialBroker)

**Fields**: domain, username, secret

**Status**: NOT-PRESENT for Devin (not used)

### SecretReference (SecretVault)

**Fields**:
- ref_id: str (UUID)
- provider: str (default "keyring")
- domain: str
- account: str
- field_role: str
- key: str (domain:account:field_role)
- created_at_utc: datetime
- available: bool

**Status**: NOT-PRESENT for Devin (not used)

### Current Devin Metadata (secrets.ps1)

**Fields available**:
- Variable name: YES (DEVIN_API_KEY, DEVIN_API_KEY_IABV, IABV_DEVIN_API_KEY)
- Raw value: YES (stored directly)
- Length: YES (observable)
- Prefix/type: PARTIAL (apk_user_* visible, but not stored as metadata)

**Fields MISSING**:
- credential ID: NOT-PRESENT
- provider: NOT-PRESENT
- account email: NOT-PRESENT
- masked email: NOT-PRESENT
- user ID: NOT-PRESENT (encoded in credential but not extracted)
- organization ID: NOT-PRESENT (encoded in credential but not extracted)
- account label: NOT-PRESENT
- credential type: NOT-PRESENT (apk_user_* vs cog_* vs other)
- API version: NOT-PRESENT (v1 vs v2 vs v3)
- creation/registration time: NOT-PRESENT
- source of credential: NOT-PRESENT (UI vs manual vs script)
- fingerprint: NOT-PRESENT
- last validation: NOT-PRESENT
- last error: NOT-PRESENT
- capability state: NOT-PRESENT

### Identity Metadata Classification

| Field | Current Status |
|-------|----------------|
| credential ID | NOT-PRESENT |
| provider | NOT-PRESENT |
| account email | NOT-PRESENT |
| masked email | NOT-PRESENT |
| user ID | CODE-ONLY (encoded in credential, not extracted) |
| organization ID | CODE-ONLY (encoded in credential, not extracted) |
| account label | NOT-PRESENT |
| credential type | PARTIAL (apk_user_* visible but not stored) |
| API version | NOT-PRESENT |
| creation/registration time | NOT-PRESENT |
| source of credential | NOT-PRESENT |
| fingerprint | NOT-PRESENT |
| last validation | NOT-PRESENT |
| last error | NOT-PRESENT |
| capability state | NOT-PRESENT |

## C. CREDENTIAL DISTINCTION

### Current Capability

**Question**: Can IABV distinguish two Devin API keys without ambiguity?

**Answer**: NO

**Current behavior**:
- All Devin credentials are stored as raw values in ~/.iabv_secrets.ps1
- Only variable name distinguishes entries (DEVIN_API_KEY_IABV, IABV_DEVIN_API_KEY, DEVIN_API_KEY)
- Resolver uses first-available fallback
- No stored metadata about which account owns each credential
- No stored metadata about which credential was tested
- No stored metadata about which credential failed or succeeded
- No way to trace a failure back to a specific credential instance

### FIRST BROKEN EDGE

**Credential distinction**: FIRST BROKEN EDGE

IABV cannot distinguish between:
- DEVIN_KEY_A (account X, org Y, type apk_user_*)
- DEVIN_KEY_B (account Z, org W, type cog_*)

Because:
1. Both are stored as raw values
2. No metadata exists to identify account/organization
3. No metadata exists to identify credential type
4. No metadata exists to track validation history
5. Resolver would return whichever is first in priority, with no trace of which one

## D. SECRET VS METADATA

### Current Coupling

**Status**: COMPLETELY COUPLED

The current implementation stores only the raw secret value:
- File: ~/.iabv_secrets.ps1
- Format: `$env:DEVIN_API_KEY = 'raw_secret_value'`
- No separation between secret and metadata
- No credential identity layer
- No audit trail for credential lifecycle

### SecretVault / CredentialBroker Design

**Status**: CORRECTLY SEPARATED (but not used for Devin)

SecretVault provides:
- **Secret**: stored in keyring (separate from metadata)
- **Metadata**: SecretReference with domain, account, field_role, created_at_utc, available
- **Separation**: SecretReference does NOT contain the secret value
- **Security**: Secret is only in keyring, metadata is in application layer

**Problem**: This correct design exists but is NOT used for Devin. Devin uses the insecure secrets.ps1 approach.

### Recommended Safe Design

For multi-credential support, IABV should:
1. Use SecretVault for credential storage (already exists)
2. Add metadata fields to SecretReference for Devin-specific attributes:
   - credential_type (apk_user_*, cog_*, etc.)
   - api_version (v1, v2, v3)
   - fingerprint (SHA-256 digest of secret)
   - last_validation_timestamp
   - last_validation_status
   - last_error
   - provider_account_id (from API response if available)
   - provider_org_id (from API response if available)
3. Keep raw secret ONLY in keyring (not in SecretReference)
4. Make SecretReference queryable for audit and selection

## E. FINGERPRINT

### Current Capability

**Status**: NOT-PRESENT

IABV currently has no non-secret fingerprint mechanism for credentials.

### Recommended Fingerprint Mechanism

**Proposal**: Truncated SHA-256 digest

```python
import hashlib

def compute_credential_fingerprint(secret: str) -> str:
    """Compute a non-secret fingerprint for credential identification."""
    return hashlib.sha256(secret.encode('utf-8')).hexdigest()[:16]
```

**Properties**:
- Deterministic: same secret always produces same fingerprint
- Non-reversible: fingerprint cannot be used to recover secret
- Stable: allows tracking same credential across validations
- Safe: can be stored in logs, evidence artifacts, and metadata

**Usage**: Fingerprint would be stored in SecretReference metadata to identify which credential was used/failed/succeeded without exposing the secret.

## F. ACCOUNT ASSOCIATION

### Current Capability

**Status**: NOT-PRESENT

IABV currently has no way to associate a credential with an account.

### Available Identity Sources

**1. Provider-returned identity**
- **Status**: NOT_IMPLEMENTED
- **Capability**: v3 API may return account/org information (requires migration)
- **Current v1 API**: No READ-ONLY endpoint to query account/org identity

**2. Identity encoded in credential**
- **Status**: PARTIALLY_AVAILABLE
- **Evidence**: apk_user_* credentials encode user_id:org_id in base64
- **Problem**: Not extracted or stored as metadata
- **Feasibility**: Could be decoded and stored as metadata without exposing raw secret

**3. User-provided account label**
- **Status**: NOT_IMPLEMENTED
- **Capability**: UI could allow user to label credentials (e.g., "devin_personal", "devin_work")
- **Safety**: Masked labels are acceptable as metadata

**4. Inferred identity**
- **Status**: NOT_PROVEN
- **Problem**: Inference is not verified identity
- **Guideline**: Do NOT treat inference as verified identity

### Recommended Approach

**Immediate**: User-provided account label (optional metadata field in SecretReference)

**Future**: Provider-returned identity via v3 API migration (when available)

**Current limitation**: If email cannot be programmatically obtained, state that explicitly (NOT_PROVEN)

## G. INDIVIDUAL VALIDATION

### Current Capability

**Status**: NOT_POSSIBLE

**Desired operation**:
```
Credential A → GET/test → result A
Credential B → GET/test → result B
```

**Current behavior**:
- `is_available()` in DevinApiToolAdapter tests the resolver's single returned credential
- No way to test multiple credentials independently
- No way to attribute result to specific credential fingerprint
- No way to track which credential failed vs succeeded

### Why It's Not Possible

1. **Single credential resolution**: `_resolve_devin_api_key()` returns only first available
2. **No credential registry**: No list of configured credentials to iterate
3. **No credential identity**: No way to distinguish Credential A from Credential B
4. **No result attribution**: Validation result cannot be linked to specific credential

### Required for Individual Validation

1. Credential registry (list of configured credentials with metadata)
2. Credential identity (fingerprint + metadata)
3. Per-credential validation logic (test each independently)
4. Result attribution (link validation result to credential fingerprint)

## H. EXISTING IABV INFRASTRUCTURE

### What Already Exists

**CredentialBroker** (services/security/credential_broker.py):
- Manages credential requests and storage
- Supports multiple accounts per domain
- Uses SecretVault for secure storage
- Has prompt handler for UI integration
- Currently NOT used for Devin

**SecretVault** (services/capture/secret_vault.py):
- Secure credential storage via keyring
- SecretReference model with metadata
- Separates secret from metadata
- Currently NOT used for Devin

**SecretReference** (domain/models.py):
- Has fields: ref_id, provider, domain, account, field_role, key, created_at_utc, available
- Correctly separates secret from metadata
- Could be extended with Devin-specific metadata

### What Missing for Devin

1. **Credential type field**: To distinguish apk_user_* vs cog_* vs other
2. **API version field**: To distinguish v1 vs v2 vs v3
3. **Fingerprint field**: To identify credentials without exposing secrets
4. **Validation tracking**: last_validation_timestamp, last_validation_status, last_error
5. **Provider identity fields**: provider_account_id, provider_org_id (when available)
6. **Integration**: Devin adapter needs to use CredentialBroker instead of secrets.ps1

## I. FIRST BROKEN EDGE

**FIRST BROKEN EDGE**: Credential distinction

IABV cannot distinguish between multiple Devin credentials because:
1. Credentials are stored as raw values in secrets.ps1
2. No metadata exists to identify account/organization/type
3. No credential registry exists
4. No fingerprint mechanism exists
5. Validation results cannot be attributed to specific credentials

All other gaps (individual validation, account association, etc.) are downstream consequences of this first broken edge.

## J. SMALLEST NEXT IMPLEMENTATION ACTION

**Option A**: Merely rename environment variables
- **Impact**: Superficial, does not solve core problem
- **Effect**: Still no metadata, no distinction, no tracking
- **Verdict**: INSUFFICIENT

**Option B**: Add a credential registry
- **Impact**: Could list credentials but without metadata
- **Effect**: Better than nothing, but still cannot distinguish or track
- **Verdict**: PARTIAL but insufficient

**Option C**: Add a credential registry + metadata + fingerprint
- **Impact**: Could list and distinguish credentials
- **Effect**: Enables multi-credential support with identity
- **Verdict**: SUFFICIENT for identity/distinction

**Option D**: Add a credential registry + metadata + fingerprint + per-credential validation
- **Impact**: Complete solution
- **Effect**: Enables identity, distinction, and validation tracking
- **Verdict**: COMPLETE but possibly more than needed immediately

**Option E**: Use existing CredentialBroker/SecretVault infrastructure
- **Impact**: Leverages existing correct design
- **Effect**: Secure credential storage with metadata separation
- **Requirement**: Extend SecretReference with Devin-specific metadata
- **Verdict**: RECOMMENDED (prefer existing infrastructure)

**RECOMMENDATION**: Option E with Option C

1. Integrate Devin with existing CredentialBroker/SecretVault (instead of secrets.ps1)
2. Extend SecretReference with Devin-specific metadata (credential_type, api_version, fingerprint)
3. Implement credential registry via CredentialBroker's existing domain/account model
4. Add fingerprint computation for credential identification
5. Per-credential validation can be added later when needed

## K. MAXIMUM VALID CLAIM

Based on code inspection:

1. **DISCOVERY**: IABV has one current source for Devin credentials (~/.iabv_secrets.ps1) and an unused alternative (CredentialBroker/SecretVault)
2. **IDENTITY METADATA**: CURRENTLY MISSING for Devin (not stored, not extracted)
3. **CREDENTIAL DISTINCTION**: NOT POSSIBLE with current implementation
4. **SECRET VS METADATA**: CURRENTLY COUPLED (raw values only), but SecretVault provides correct separation
5. **FINGERPRINT**: NOT IMPLEMENTED
6. **ACCOUNT ASSOCIATION**: NOT IMPLEMENTED
7. **INDIVIDUAL VALIDATION**: NOT POSSIBLE
8. **FIRST BROKEN EDGE**: Credential distinction (cannot distinguish multiple credentials)
9. **EXISTING INFRASTRUCTURE**: CredentialBroker/SecretVault exists with correct design but is NOT used for Devin
10. **RECOMMENDED ACTION**: Integrate Devin with existing CredentialBroker/SecretVault and extend SecretReference with Devin-specific metadata

**NOT PROVEN**:
- Multi-credential routing needed (only one credential currently exists)
- Credential type restriction causes 403 (not verified)
- Organization quota is the blocker (cannot be verified without READ-ONLY access)

## L. LIMITATIONS

- No evidence that multiple Devin credentials currently exist
- No evidence that multi-credential routing is immediately required
- Current v1 credential limitation (no READ-ONLY quota/billing endpoints) persists regardless of credential architecture
- UI observation of account state was not completed (R4.4-K) due to browser preview limitation

## M. NEXT CAUSAL EDGE

Before implementing multi-credential support, determine:
1. Does the user actually have multiple Devin credentials?
2. If yes, are they for different organizations with different quotas?
3. If yes, multi-credential selection would actually help

If the answer to any question is NO, then multi-credential support is premature.

The next experimental step should be to determine the actual account state (R4.4-K) before committing to architectural changes for multi-credential routing.
