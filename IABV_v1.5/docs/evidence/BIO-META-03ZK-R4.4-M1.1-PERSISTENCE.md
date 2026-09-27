# BIO-META-03ZK-R4.4-M1.1 — PERSISTENT DEVIN ACCOUNT/CREDENTIAL REGISTRY

## PROVENANCE

**Repository**: jhonf463r/Python
**Subdirectory**: IABV_v1.5/
**Branch**: devin/bio-meta-03n-controlmaster-external-path
**Start SHA**: 4da2924c6238582ceb87aaa65d25c79c6cafff3e
**Implementation SHA**: (pending commit)
**Evidence SHA**: (pending commit)
**Parent**: 4da2924c6238582ceb87aaa65d25c79c6cafff3e
**Runtime**: Windows, Python 3.13.2
**Timestamp**: 2026-09-27

## OBJECTIVE

Convert the M1 in-memory Devin account/credential registry into a persistent registry that survives IABV restart.

Required lifecycle:
```
register account → persist → register credential → persist → validate credential → persist validation metadata → restart service → reload registry → same account_id, credential_id, fingerprint, validation metadata
```

## PERSISTENCE DESIGN

### Existing Persistence Infrastructure Reused

The existing IABV persistence architecture under `src/iabv_v15/infra/persistence/` was inspected and found suitable:

- **AppDatabase**: Central SQLite database with WAL mode, busy timeout, and existing schema
- **Repository pattern**: Existing repositories for episodes, knowledge, runs, sessions, etc.
- **Pydantic JSON serialization**: Models serialized as JSON in TEXT columns
- **Indexes**: Existing indexes for performance

Why this is semantically appropriate:
- Devin account/credential metadata is domain state, similar to episodes, knowledge items, or execution dossiers
- The repository pattern is already established for all durable domain state
- Reusing AppDatabase avoids creating a second database or persistence subsystem
- SQLite provides ACID guarantees and is already used for IABV state

### Files/Models Changed

**New file**: `src/iabv_v15/infra/persistence/devin_account_repository.py`
- Implements `DevinAccountRepository` class
- Methods: `save_account()`, `get_account()`, `list_accounts()`, `delete_account()`, `save_credential()`, `get_credential()`, `list_credentials()`, `delete_credential()`
- Serializes `DevinAccount` and `DevinCredential` models as JSON
- Stores only metadata, never raw secrets

**Modified**: `src/iabv_v15/infra/persistence/database.py`
- Added `devin_accounts` table with columns: account_id, provider, display_label, email, organization_id, organization_label, plan, browser_profile_id, identity_source, identity_verified, account_json, created_at_utc, updated_at_utc
- Added `devin_credentials` table with columns: credential_id, account_id, secret_ref_id, fingerprint, credential_type, api_version, source, validation_status, last_validated_at, last_http_status, last_error_code, last_error_summary, capabilities_json, credential_json, created_at_utc, updated_at_utc
- Added indexes: idx_devin_accounts_provider, idx_devin_accounts_email, idx_devin_credentials_account, idx_devin_credentials_fingerprint, idx_devin_credentials_status

**Modified**: `src/iabv_v15/services/providers/devin_account_service.py`
- Constructor now accepts optional `DevinAccountRepository` parameter
- In-memory-only mode still supported when `repository=None`
- All registration, lookup, listing, and validation methods now persist metadata when repository is available
- Persistence calls added after account/credential registration and validation updates

**New file**: `tests/test_devin_persistence.py`
- 11 focused tests for persistence behavior
- Tests: account survives restart, credential survives restart, account_id stable, credential_id stable, fingerprint stable, multiple credentials distinct, multiple accounts distinct, validation metadata survives restart, raw secrets never in persistence, unknown account identity not verified, persistence without repository

**New file**: `tests/test_devin_m1_1_runtime_validation.py`
- Runtime validation script using the existing DEVIN_API_KEY
- Demonstrates full lifecycle: register → persist → validate → persist → restart → reload → recover

## SECURITY MODEL

### Raw Secret Location

Raw credentials are stored exclusively in:
- **SecretVault**: `src/iabv_v15/services/capture/secret_vault.py`
- **OS keyring**: Where available (Windows Credential Manager, macOS Keychain, Linux secret-service)

### Metadata Location

Credential and account metadata are stored in:
- **SQLite database**: `devin_accounts` and `devin_credentials` tables
- **JSON columns**: `account_json` and `credential_json` store Pydantic model dumps

### Fingerprint

- **Algorithm**: SHA-256 truncated to 8 hexadecimal characters (32 bits)
- **Deterministic**: Same secret always produces same fingerprint
- **Non-reversible**: Truncated hash cannot reconstruct the original secret
- **Safe for logging/evidence**: Fingerprint can be stored in logs, evidence, and metadata without exposing the secret

### Never Persisted

The following are NEVER persisted in the registry:
- API keys
- Authorization headers
- Passwords
- Cookies
- Browser tokens
- MFA data
- Raw credential values

### SecretReference Linkage

The `secret_ref_id` in `devin_credentials` table references a `SecretReference` object. The actual secret is resolved through `SecretVault` at runtime, not stored in the registry.

## RESTART TEST

### Before Restart

```
Account registered: 106036c5-e8cd-46ca-a9e2-6ba42698510c
display_label: legacy_devin_account
identity_source: unknown
identity_verified: False

Credential registered: 9b22338c-2c78-4c7c-980a-a03b44e1940e
fingerprint: 09f03f3c051929f8
credential_type: apk_user
api_version: v1
source: legacy
```

### Persisted

Metadata persisted to SQLite database:
- Account record in `devin_accounts` table
- Credential record in `devin_credentials` table
- Validation metadata (last_validated_at, last_http_status, etc.) in credential record

### After Restart

New service instance created with same repository.

### Recovered

```
Account recovered: 106036c5-e8cd-46ca-a9e2-6ba42698510c
account_id matches: True
display_label: legacy_devin_account
identity_source: unknown

Credential recovered: 9b22338c-2c78-4c7c-980a-a03b44e1940e
credential_id matches: True
fingerprint matches: True
fingerprint: 09f03f3c051929f8
credential_type: apk_user
api_version: v1
source: legacy
validation_status: ready
last_validated_at: 2026-09-27 02:30:21.338021+00:00
last_http_status: 200
last_error_code: None
```

All IDs, fingerprint, and validation metadata preserved across restart.

## RUNTIME VALIDATION

### Credential Fingerprint

**Fingerprint**: 09f03f3c051929f8
**Credential type**: apk_user (v1/v2 legacy personal API key)
**API version**: v1
**Source**: legacy

### HTTP Status

**HTTP status**: 200
**Latency**: 1699.89ms
**Endpoint**: GET https://api.devin.ai/v1/sessions?limit=1

### Validation Status

**Validation status**: ready
**Last validated at**: 2026-09-27 02:30:21.338021+00:00
**Last HTTP status**: 200
**Last error code**: None

### Verification

- [OK] Account metadata survived restart
- [OK] Credential metadata survived restart
- [OK] account_id remained stable
- [OK] credential_id remained stable
- [OK] fingerprint remained stable
- [OK] validation metadata survived restart
- [OK] raw secret available in SecretVault
- [OK] raw secret NOT in persisted metadata

## BROWSER LINKAGE LIMITATIONS

### Existing Browser Infrastructure

Inspected the following components:
- `BrowserSessionController`: Playwright controller for browser sessions, supports persistent user data directories and storage state
- `BrowserProfileConfig`: Configuration model for browser profiles
- `BrowserTeachSessionService`: Service for browser teach sessions

### Current Capability

The `browser_profile_id` field in `DevinAccount` can provide a stable linkage:
```
DevinAccount
    ↕
browser_profile_id
    ↕
persistent browser profile (via BrowserSessionController)
```

### First Missing Integration Edge

The missing edge is the integration between browser-based account registration and `DevinAccount`:

**Current state**:
- `DevinAccount` has `browser_profile_id` field
- `BrowserSessionController` can manage persistent browser profiles
- No service exists to: open app.devin.ai → observe identity → confirm with user → register account → set browser_profile_id

**Required future implementation**:
1. Service to orchestrate browser-based account registration
2. Identity observation from app.devin.ai (email, organization, plan)
3. User confirmation flow in UI
4. Linkage of observed browser profile to `DevinAccount.browser_profile_id`

This is explicitly out of scope for M1.1 and will be addressed in a later phase.

## TESTS

### Unit Tests

**File**: `tests/test_devin_persistence.py`
**Count**: 11 tests
**Result**: 11/11 passed

Tests cover:
- Account survives restart
- Credential survives restart
- account_id remains stable
- credential_id remains stable
- fingerprint remains stable
- Multiple credentials remain distinct
- Multiple accounts remain distinct
- Validation metadata survives restart
- Raw secrets are never persisted in registry metadata
- Unknown account identity remains identity_verified = false
- Persistence without repository (in-memory only)

### M1 Regression Tests

**File**: `tests/test_devin_account_service.py`
**Count**: 23 tests
**Result**: 23/23 passed

No regressions introduced by M1.1 persistence changes.

### Runtime Validation

**File**: `tests/test_devin_m1_1_runtime_validation.py`
**Result**: All checks passed

Demonstrated actual restart/reload boundary with the existing DEVIN_API_KEY.

## MAXIMUM VALID CLAIM

Based on the evidence above, the maximum valid claim is:

1. Devin account and credential metadata can be persisted to SQLite using the existing IABV persistence architecture
2. Account IDs, credential IDs, and fingerprints remain stable across restart
3. Validation metadata (timestamp, HTTP status, error code) survives restart
4. Raw secrets are stored in SecretVault and never persisted in the registry
5. The registry can reload metadata after a service restart without requiring re-entry of the secret
6. Multiple accounts and multiple credentials can coexist in the persistent registry
7. The existing legacy DEVIN_API_KEY can be migrated and validated without deletion
8. The `browser_profile_id` field exists in `DevinAccount` for future browser linkage

**NOT claimed**:
- Browser-based account registration (not implemented)
- Automatic multi-account routing (not implemented)
- UI integration for account management (not implemented)
- v3 credential validation (not implemented)
- Production Devin traffic migration (not implemented)

## NEXT CAUSAL EDGE

**Browser-based account registration**

The next edge is to implement the integration between browser infrastructure and `DevinAccount`:
- Open app.devin.ai in a dedicated browser profile
- Observe account identity (email, organization, plan)
- Present identity summary to user for confirmation
- Register account with `identity_source = USER_CONFIRMED_BROWSER`
- Set `browser_profile_id` to link the persistent browser profile
- Enable credential onboarding flow for the confirmed account

This phase will establish the browser identity → account registration → credential onboarding chain that M1.1 laid the foundation for.

## FILES CHANGED

- `src/iabv_v15/infra/persistence/database.py` (added Devin tables and indexes)
- `src/iabv_v15/infra/persistence/devin_account_repository.py` (new file)
- `src/iabv_v15/services/providers/devin_account_service.py` (integrated repository)
- `tests/test_devin_persistence.py` (new file)
- `tests/test_devin_m1_1_runtime_validation.py` (new file)

## GIT STATUS

Pending commit.
