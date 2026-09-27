# BIO-META-03ZK-R4.4-M1 — Devin Account & Credential Management

## Provenance

- **Repository**: jhonf463r/Python
- **Subdirectory**: IABV_v1.5/
- **Branch**: devin/bio-meta-03n-controlmaster-external-path
- **HEAD**: f6225bf98
- **Parent**: 97e6bbdfc192cd832d85bd4962c47b62bef733ae

## Changed Architecture Surface

### New Models (domain/models.py)

**IdentitySource** (Enum):
- USER_CONFIRMED_BROWSER
- PROVIDER_RETURNED
- USER_PROVIDED
- INFERRED
- UNKNOWN

**CredentialType** (Enum):
- APK_USER (v1/v2 legacy personal API key)
- APK (v1/v2 API key)
- COG (v3 service user token)
- UNKNOWN

**ApiVersion** (Enum):
- V1
- V2
- V3
- UNKNOWN

**ValidationStatus** (Enum):
- READY
- DEGRADED
- BLOCKED
- UNVERIFIED
- ERROR

**DevinAccount** (BaseModel):
- account_id (UUID)
- provider
- display_label
- email (masked)
- organization_id
- organization_label
- plan
- browser_profile_id
- identity_source (IdentitySource)
- identity_verified (bool)
- created_at_utc
- updated_at_utc

**DevinCredential** (BaseModel):
- credential_id (UUID)
- account_id (reference to DevinAccount)
- secret_reference (SecretReference - raw secret in keyring)
- fingerprint (truncated SHA-256)
- credential_type (CredentialType)
- api_version (ApiVersion)
- source (e.g., "legacy", "browser", "user_provided")
- validation_status (ValidationStatus)
- last_validated_at
- last_http_status
- last_error_code
- last_error_summary
- capabilities (dict)
- created_at_utc
- updated_at_utc

### New Service (services/providers/devin_account_service.py)

**DevinAccountService**:
- register_account() - Register account with observed/user-provided identity
- get_account() - Retrieve account by ID
- list_accounts() - List all registered accounts
- register_credential() - Register credential with secure SecretVault storage
- get_credential() - Retrieve credential by ID
- list_credentials() - List credentials (optionally filtered by account)
- get_credential_secret() - Retrieve raw secret from SecretVault
- validate_credential_read_only() - READ-ONLY health check
- migrate_existing_credential() - Migrate legacy credential without deletion

**Helper Functions**:
- compute_credential_fingerprint() - Truncated SHA-256 (non-reversible)
- classify_credential_type() - Classify from prefix (apk_user_*, apk_*, cog_*)
- classify_api_version() - Classify from prefix (v1, v2, v3)

## Existing Organs Reused

**SecretVault** (services/capture/secret_vault.py):
- Secure credential storage via keyring
- Separates secret from metadata
- Used for raw secret storage (domain="devin", account=credential_id, field_role="api_key")

**SecretReference** (domain/models.py):
- Existing model for metadata-only credential reference
- Extended for Devin credentials
- Contains ref_id, provider, domain, account, field_role, key, created_at_utc, available

**ProviderStatus** (domain/models.py):
- Existing enum for provider health status
- Reused via ValidationStatus enum (READY, DEGRADED, UNAVAILABLE, etc.)

**BrowserProfileConfig** (domain/models.py):
- Existing model for browser profile configuration
- Can be used for browser-based account registration (future)

## Account Model

**Purpose**: Registry entry for a Devin account with identity metadata.

**Key Fields**:
- display_label: User-provided label (e.g., "devin_personal", "devin_work")
- email: Masked email from browser/API
- organization_id: From API or browser
- organization_label: User-provided org label
- plan: From browser (self-serve, Enterprise, etc.)
- browser_profile_id: BrowserProfileConfig.profile_id if applicable
- identity_source: Explicit source of identity (USER_CONFIRMED_BROWSER, PROVIDER_RETURNED, etc.)
- identity_verified: Boolean based on identity_source

**Identity Source Confidence**:
- USER_CONFIRMED_BROWSER: identity_verified = True
- PROVIDER_RETURNED: identity_verified = True
- USER_PROVIDED: identity_verified = False
- INFERRED: identity_verified = False
- UNKNOWN: identity_verified = False

## Credential Model

**Purpose**: Registry entry for a Devin API credential with secure storage and validation metadata.

**Key Fields**:
- account_id: Reference to DevinAccount.account_id
- secret_reference: SecretReference (raw secret in keyring, NOT in credential metadata)
- fingerprint: Truncated SHA-256 (non-reversible, for identification)
- credential_type: APK_USER, APK, COG, UNKNOWN
- api_version: V1, V2, V3, UNKNOWN
- source: "legacy", "browser", "user_provided", etc.
- validation_status: READY, DEGRADED, BLOCKED, UNVERIFIED, ERROR
- last_validated_at: Timestamp of last READ-ONLY validation
- last_http_status: HTTP status from last validation
- last_error_code: Error code from last validation
- last_error_summary: Human-readable error summary
- capabilities: Dict for future capability tracking (session_create, quota_available, etc.)

**Security Model**:
- Raw secret stored ONLY in SecretVault (keyring)
- SecretReference contains metadata only (NO secret)
- DevinCredential contains metadata only (NO secret)
- Fingerprint is non-reversible (cannot reconstruct secret)
- Fingerprint can be stored in logs, evidence, and metadata

## Identity Source Model

**Purpose**: Explicit tracking of how account identity was obtained.

**Sources**:
- USER_CONFIRMED_BROWSER: User confirmed identity observed in browser
- PROVIDER_RETURNED: Identity returned by provider API
- USER_PROVIDED: User manually provided identity
- INFERRED: Identity inferred by IABV (NOT verified)
- UNKNOWN: Identity source unknown

**Confidence**:
- High confidence: USER_CONFIRMED_BROWSER, PROVIDER_RETURNED
- Medium confidence: USER_PROVIDED
- Low confidence: INFERRED
- No confidence: UNKNOWN

**Never silently convert inference to verified ownership**:
- Identity inference must be explicitly marked as INFERRED
- Only user confirmation or provider return can mark identity_verified = True

## Security Model

**Separation of Concerns**:
- Raw secret: Stored in SecretVault (keyring) only
- Credential metadata: Stored in DevinCredential (no secret)
- Account metadata: Stored in DevinAccount (no secret)
- Fingerprint: Stored in DevinCredential (non-reversible)

**Secret Safety**:
- SecretVault uses OS keyring where available
- SecretReference does NOT contain the secret
- DevinCredential does NOT contain the secret
- DevinAccount does NOT contain the secret
- Fingerprint cannot reconstruct secret (truncated SHA-256)

**Fingerprint Properties**:
- Deterministic: same secret always produces same fingerprint
- Non-reversible: fingerprint cannot reconstruct secret
- Stable: allows tracking same credential across validations
- Safe: can be stored in logs, evidence artifacts, and metadata

## Tests

**Unit Tests** (tests/test_devin_account_service.py):
- test_fingerprint_deterministic - Identical secrets produce identical fingerprints
- test_fingerprint_distinguishes_secrets - Fingerprints distinguish two different secrets
- test_fingerprint_non_reversible - Fingerprint cannot reconstruct secret
- test_classify_credential_type_apk_user - Classify apk_user_* credentials
- test_classify_credential_type_apk - Classify apk_* credentials
- test_classify_credential_type_cog - Classify cog_* credentials
- test_classify_credential_type_unknown - Classify unknown credentials
- test_classify_api_version_v1 - Classify v1/v2 credentials from prefix
- test_classify_api_version_v3 - Classify v3 credentials from prefix
- test_classify_api_version_unknown - Classify unknown API version
- test_register_account_basic - Basic account registration
- test_register_account_with_browser_source - Account registration with browser-confirmed identity
- test_list_accounts - List multiple accounts
- test_register_credential_basic - Basic credential registration
- test_register_credential_unknown_account - Register credential for unknown account raises error
- test_two_credentials_coexist - Two credentials can coexist in metadata without exposing secrets
- test_list_credentials_by_account - List credentials filtered by account
- test_identity_source_preserved - Account identity source is preserved
- test_unknown_account_ownership_not_verified - Unknown account ownership remains NOT_VERIFIED
- test_migrate_existing_credential - Existing legacy credential can be registered without deletion
- test_validation_result_attribution - Validation results are attributed to the exact credential fingerprint
- test_validate_unknown_credential - Validate unknown credential returns error
- test_raw_secrets_not_in_metadata - Raw secrets are never emitted to credential metadata

**Test Results**: 23/23 passed

**Runtime Validation Test** (tests/test_devin_m1_runtime_validation.py):
- Demonstrates existing credential → registry lookup → fingerprint → SecretVault resolution → READ-ONLY validation → persistent validation record
- Uses REAL existing credential but does NOT create a Devin session
- Validates GET /v1/sessions?limit=1 → HTTP 200

## Runtime Validation

**Existing Credential**:
- Variable: DEVIN_API_KEY
- Prefix: apk_user_*
- Length: 153 characters
- Fingerprint: 09f03f3c051929f8
- Credential type: apk_user (v1/v2 legacy personal API key)
- API version: v1
- Source: legacy

**Validation Path**:
1. Load existing credential from environment (bootstrap)
2. Register placeholder account (identity_verified = False)
3. Migrate existing credential into registry (source = "legacy")
4. Compute fingerprint (09f03f3c051929f8)
5. Store secret in SecretVault (keyring)
6. Perform READ-ONLY validation (GET /v1/sessions?limit=1)
7. Update credential metadata with validation result
8. Verify secret retrievable from SecretVault
9. Verify fingerprint non-reversible

**Validation Result**:
- Valid: True
- HTTP status: 200
- Error code: None
- Error summary: (empty)
- Latency: 1638.04ms
- Validation status: ready
- Last validated at: 2026-09-27T02:07:22.993641+00:00

**Persistent Validation Record**:
- credential_id: c34d78af-52af-4c8b-9a19-6dfa6ff0137a
- fingerprint: 09f03f3c051929f8
- validation_status: ready
- last_validated_at: 2026-09-27T02:07:22.993641+00:00
- last_http_status: 200
- last_error_code: None
- last_error_summary: (empty)

## Limitations

**Current Implementation**:
- v3 validation not yet implemented (placeholder returns error)
- Browser-based account registration not yet implemented (model exists but no service integration)
- Persistence is in-memory only (no disk persistence yet)
- No UI integration yet (models and service exist but no ViewModel)

**Security Limitations**:
- Account identity from API v1 is NOT_AVAILABLE (requesting_user_email field exists but was empty in M0)
- Account ownership cannot be verified without provider-provided identity
- Identity verification depends on browser observation or provider API

**Architecture Limitations**:
- No automatic multi-account routing (NOT IMPLEMENTED - future capability)
- No credential selection based on quota (NOT IMPLEMENTED - future capability)
- No automatic session creation or billing management (NOT IMPLEMENTED - future capability)

## Maximum Valid Claim

Based on implementation and runtime validation:

1. **ACCOUNT MODEL**: Implemented with identity source tracking and verification flags
2. **CREDENTIAL MODEL**: Implemented with secure SecretVault storage and validation metadata
3. **FINGERPRINT MECHANISM**: Implemented (truncated SHA-256, non-reversible)
4. **IDENTITY SOURCE MODEL**: Implemented with explicit confidence levels
5. **SECURITY MODEL**: Raw secrets separated from metadata, stored in SecretVault
6. **EXISTING INFRASTRUCTURE REUSED**: SecretVault, SecretReference, ProviderStatus patterns
7. **UNIT TESTS**: 23/23 passed, covering all required scenarios
8. **RUNTIME VALIDATION**: Existing credential successfully registered and validated
9. **VALIDATION ATTRIBUTION**: Results attributed to exact credential fingerprint
10. **LEGACY CREDENTIAL MIGRATION**: Existing credential can be registered without deletion

**NOT IMPLEMENTED**:
- Automatic multi-account routing
- Browser-based account registration (service integration)
- Disk persistence (registry is in-memory only)
- UI integration
- v3 validation

**NOT PROVEN**:
- Account identity from provider API (v1 does not return usable identity)
- Multiple credentials actually exist (only one currently exists)
- Multi-account routing is needed (only one credential currently exists)

## Next Causal Edge

**NEXT EDGE**: Browser-based account registration

This would enable:
- IABV opens dedicated browser profile
- User authenticates at app.devin.ai
- IABV observes visible account identity (email, organization, plan)
- User explicitly confirms identity
- Account profile becomes registered with identity_source = USER_CONFIRMED_BROWSER

This edge requires:
- Integration with BrowserSessionController / BrowserTeachSessionService
- Observation and redaction of visible identity information
- User confirmation flow via UI
- Association of observed identity with account record

This edge is separate from M1 and should be explored after persistence is added to the registry.

## Stop Condition

M1 successfully implemented:
- Account/credential models with identity source tracking
- Secure SecretVault integration
- Fingerprint mechanism
- READ-ONLY validation
- Unit tests (23/23 passed)
- Runtime validation of existing credential

Did NOT implement:
- Automatic multi-account routing
- Browser-based account registration
- Disk persistence
- UI integration

All stop conditions respected.
