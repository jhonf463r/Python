# P0.213 V5R16 — Dual State Authority Analysis

**Document Purpose**: Document all active and inert state authority paths in the codebase  
**Status**: P0_213_V5R16_PROTOCOL_UNIFICATION_IN_PROGRESS

---

## 1. JOIN STATE AUTHORITIES

### 1.1 Canonical Join State (ACTIVE)

**Path**: AuthorityService → authority_join_authorizations.db  
**Table**: join_authorizations  
**Handlers**:
- `AuthorityService.handle_phase3_request_join()` (NEW - unified transport path)
- `AuthorityService.handle_phase3_request_challenge()` (NEW - unified transport path)
- `AuthorityService.handle_phase3_redeem_join()` (NEW - unified transport path)

**Schema**:
```sql
CREATE TABLE join_authorizations (
    join_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    execution_id TEXT NOT NULL,
    generation INTEGER NOT NULL,
    client_pid INTEGER NOT NULL,
    public_key TEXT NOT NULL,
    created_at REAL NOT NULL,
    consumed INTEGER NOT NULL DEFAULT 0,
    consumed_at REAL,
    UNIQUE(subject_id, execution_id, generation)
)
```

**Status**: ACTIVE - This is the canonical state authority for Phase 3.

### 1.2 Legacy Join State (INERT)

**Path**: Phase3AuthorityExtension → phase3_join_state.db  
**Table**: join_tokens  
**Handlers**:
- `Phase3AuthorityExtension.handle_request_join()` (DEPRECATED)
- `Phase3AuthorityExtension.handle_request_challenge()` (DEPRECATED)
- `Phase3AuthorityExtension.handle_redeem_join()` (DEPRECATED)

**Schema**:
```sql
CREATE TABLE join_tokens (
    join_token TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    public_key TEXT NOT NULL,
    pinned INTEGER NOT NULL DEFAULT 0,
    redeemed INTEGER NOT NULL DEFAULT 0,
    generation INTEGER NOT NULL,
    pinned_at REAL NOT NULL,
    redeemed_at REAL,
    consumer_pid INTEGER,
    task_context TEXT,
    episode_id TEXT,
    session_id TEXT
)
```

**Status**: INERT - All handlers emit DeprecationWarning. Still functional for backward compatibility but should not be used in production.

**References**: Only referenced in `phase3_authority.py:51`

---

## 2. CHALLENGE STATE AUTHORITIES

### 2.1 Canonical Challenge State (ACTIVE)

**Path**: AuthorityService → authority_challenge_state.db  
**Table**: challenges  
**Handlers**:
- `AuthorityService.handle_phase3_request_challenge()` (NEW - unified transport path)
- `AuthorityService.handle_phase3_redeem_join()` (NEW - unified transport path)

**Schema**:
```sql
CREATE TABLE challenges (
    challenge_id TEXT PRIMARY KEY,
    join_id TEXT NOT NULL,
    challenge TEXT NOT NULL,
    generation INTEGER NOT NULL,
    issued_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    consumed INTEGER NOT NULL DEFAULT 0,
    consumed_at REAL,
    UNIQUE(join_id, challenge)
)
```

**Status**: ACTIVE - This is the canonical state authority for Phase 3 challenges.

### 2.2 Legacy Challenge State (INERT)

**Path**: Phase3AuthorityExtension → phase3_challenge_state.db  
**Table**: challenges  
**Handlers**:
- `Phase3AuthorityExtension.handle_request_challenge()` (DEPRECATED)
- `Phase3AuthorityExtension.handle_redeem_join()` (DEPRECATED)

**Schema**:
```sql
CREATE TABLE challenges (
    challenge_id TEXT PRIMARY KEY,
    join_token TEXT NOT NULL,
    challenge TEXT NOT NULL,
    generation INTEGER NOT NULL,
    issued_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    subject_id TEXT,
    execution_id TEXT
)
```

**Status**: INERT - All handlers emit DeprecationWarning. Still functional for backward compatibility but should not be used in production.

---

## 3. SUBJECT REGISTRY AUTHORITIES

### 3.1 Canonical Subject Registry (ACTIVE)

**Path**: AuthorityService → run_records.db  
**Table**: run_records  
**Handlers**:
- `AuthorityService.handle_register_execution()` (Phase 2)
- `AuthorityService._resolve_subject_from_run_record()` (Phase 3 unified path)

**Status**: ACTIVE - This is the canonical subject registry for both Phase 2 and Phase 3.

### 3.2 Legacy Subject Registry (INERT)

**Path**: AuthenticationLayer → authorized_subjects.db  
**Table**: authorized_subjects  
**Handlers**:
- `AuthenticationLayer.register_subject()` (DEPRECATED)
- `AuthenticationLayer.revoke_subject()` (DEPRECATED)
- `AuthenticationLayer.validate_subject_key_binding()` (DEPRECATED)

**Status**: INERT - Only used by deprecated Phase3AuthorityExtension. The unified path uses RunRecord instead.

---

## 4. GENERATION AUTHORITIES

### 4.1 Canonical Generation Authority (ACTIVE)

**Path**: AuthorityService → run_records.generation  
**Handlers**:
- `AuthorityService.handle_register_execution()` (Phase 2)
- `AuthorityService.handle_phase3_request_join()` (Phase 3 unified path)
- `AuthorityService.handle_phase3_request_challenge()` (Phase 3 unified path)
- `AuthorityService.handle_phase3_redeem_join()` (Phase 3 unified path)

**Status**: ACTIVE - Single source of truth for generation across all phases.

### 4.2 Legacy Generation Authority (NONE)

**Status**: NONE - No legacy generation authority exists. Both paths correctly use run_records.generation.

---

## 5. SUMMARY OF ACTIVE VS INERT PATHS

| Component | Canonical Path | Legacy Path | Status |
| --------- | -------------- | ----------- | ------ |
| Join State | authority_join_authorizations.db | phase3_join_state.db | Canonical ACTIVE, Legacy INERT |
| Challenge State | authority_challenge_state.db | phase3_challenge_state.db | Canonical ACTIVE, Legacy INERT |
| Subject Registry | run_records.db (RunRecord) | authorized_subjects.db | Canonical ACTIVE, Legacy INERT |
| Generation | run_records.generation | N/A | Single ACTIVE |

---

## 6. SECURITY DECISION AUTHORITY

**Current State**: No duplicate security decision authority exists.

**Reasoning**:
- The legacy Phase3AuthorityExtension handlers are marked DEPRECATED and emit warnings
- The unified path in AuthorityService is the only ACTIVE path for new Phase 3 operations
- The legacy databases (phase3_join_state.db, phase3_challenge_state.db, authorized_subjects.db) are only accessed by deprecated handlers
- No security decision can be made by both canonical and legacy implementations simultaneously

**Conclusion**: The dual state authority issue has been resolved by making the legacy path inert. The canonical path is the only active authority.

---

## 7. MIGRATION STATUS

### Phase 1: Extend New Path ✅ COMPLETE
- ✅ Add public_key column to join_authorizations
- ✅ Create authority_challenge_state.db
- ✅ Add handle_phase3_request_challenge()
- ✅ Add handle_phase3_redeem_join()
- ✅ Update AuthorityServer routing

### Phase 2: Make Legacy Inert ✅ COMPLETE
- ✅ Add DeprecationWarning to Phase3AuthorityExtension handlers
- ✅ Document legacy path as deprecated

### Phase 3: Remove Legacy ⏳ PENDING
- ⏳ Remove Phase3AuthorityExtension class
- ⏳ Delete phase3_join_state.db
- ⏳ Delete phase3_challenge_state.db
- ⏳ Delete authorized_subjects.db
- ⏳ Remove authentication_layer.py (or repurpose)

**Note**: Phase 3 is deferred to allow for backward compatibility testing before complete removal.

---

**Document End**
