# P0.213 V5R16 — AUTHORITY CHAIN ANALYSIS

**Analysis Date**: 2026-08-22  
**Purpose**: Document caller → transport → authority server → authority service → Phase3AuthorityExtension chain

---

## 1. EXISTING AUTHORITY INFRASTRUCTURE

### Phase 2 Authority System (RUNTIME_VERIFIED)

**Location**: `src/iabv_v15/services/trust/`

#### authority_server.py
- **Purpose**: Windows Named Pipe server for IPC boundary
- **Security**: Explicit DACL, OS-observed client identity
- **Identity Verification**: `GetNamedPipeClientProcessId(pipe_handle)` → actual OS PID
- **Request Types**: REGISTER_EXECUTION, ISSUE_LEASE, CONSUME_LEASE, VERIFY_EXECUTION, GET_STATUS
- **Status**: RUNTIME_VERIFIED (real Windows IPC)

#### authority_service.py
- **Purpose**: Trusted authority process service
- **Security**: Owns real secret key, generation state, lease state
- **Identity Verification**: Uses client_pid from authority_server (OS-observed)
- **Status**: RUNTIME_VERIFIED (separate trusted authority process)

### Phase 3 Authority System (PARTIALLY IMPLEMENTED)

**Location**: `src/iabv_v15/services/phase3/`

#### authentication_layer.py
- **Purpose**: Authentication layer for Phase 3 authorization
- **Security**: AuthorizationSubject registry, subject/key binding
- **Identity Verification**: `verify_caller_identity(client_pid)` → **PLACEHOLDER** (returns True, None)
- **Status**: PARTIALLY IMPLEMENTED (Windows-specific placeholder)

#### phase3_authority.py
- **Purpose**: Phase 3 authority extension
- **Request Types**: REQUEST_JOIN, REQUEST_CHALLENGE, REDEEM_JOIN
- **Integration**: Uses authentication_layer for identity verification
- **Status**: PARTIALLY IMPLEMENTED

---

## 2. AUTHORITY CHAIN DOCUMENTATION

### Current State (DISCONNECTED)

```
Phase 2 Authority System (RUNTIME_VERIFIED):
caller process
    ↓
Windows Named Pipe (\\.\pipe\IABV_Authority)
    ↓
authority_server.py (GetNamedPipeClientProcessId)
    ↓
authority_service.py (client_pid verification)
    ↓
REGISTER_EXECUTION / ISSUE_LEASE / CONSUME_LEASE

Phase 3 Authority System (PARTIALLY IMPLEMENTED):
caller process
    ↓
??? (no defined transport)
    ↓
Phase3AuthorityExtension.handle_request_join
    ↓
authentication_layer.verify_caller_identity (PLACEHOLDER)
    ↓
REQUEST_JOIN / REQUEST_CHALLENGE / REDEEM_JOIN
```

### Gap Identified

**Phase 3 has NO defined transport layer** and **NO real Windows identity verification**.

The Phase 3 system appears to be a separate, disconnected authorization mechanism that:
1. Does not use the Phase 2 authority_server/authority_service
2. Has placeholder Windows identity verification
3. Has no defined IPC transport (unlike Phase 2's Named Pipe)
4. Has no authoritative subject registry bootstrap

---

## 3. AUTHORIZATION SUBJECT REGISTRY

### Current Implementation

**Location**: `authentication_layer.py`

**Database**: `authorized_subjects.db` (SQLite)

**Schema**:
```sql
CREATE TABLE authorized_subjects (
    subject_id TEXT PRIMARY KEY,
    windows_sid TEXT,
    allowed_public_keys TEXT (JSON),
    parent_authority TEXT,
    created_at REAL,
    is_active INTEGER
)
```

**Registration Method**: `register_subject(subject_id, windows_sid, allowed_public_keys, parent_authority)`

**Issue**: Only referenced by tests, no production bootstrap path

---

## 4. REQUIRED INTEGRATION

### Option 1: Integrate Phase 3 with Phase 2 Authority

**Approach**: Make Phase 3 use the existing Phase 2 authority infrastructure

**Benefits**:
- Leverages RUNTIME_VERIFIED Windows identity verification
- Uses existing authority_server/authority_service
- Consistent security boundary

**Changes Required**:
1. Add REQUEST_JOIN/REQUEST_CHALLENGE/REDEEM_JOIN handlers to authority_service.py
2. Route Phase 3 requests through authority_server.py
3. Remove authentication_layer.py placeholder
4. Use Phase 2's OS-observed client_pid for Phase 3 authorization

### Option 2: Implement Real Windows Identity Verification for Phase 3

**Approach**: Implement actual Windows identity verification in authentication_layer.py

**Benefits**:
- Keeps Phase 3 as separate authorization system
- Allows independent Phase 3 security boundary

**Changes Required**:
1. Implement `verify_caller_identity` using Windows security API
2. Use `OpenProcessToken`, `GetTokenInformation` to get process SID
3. Define transport layer for Phase 3 (or integrate with existing transport)
4. Implement authoritative subject registry bootstrap

---

## 5. RECOMMENDATION

**Option 1 is preferred** because:
1. Phase 2 authority is already RUNTIME_VERIFIED
2. Avoids duplicating Windows identity verification code
3. Provides consistent security boundary across all phases
4. Leverages existing trusted authority process

**Implementation Path**:
1. Add Phase 3 request handlers to authority_service.py
2. Integrate AuthorizationSubject registry with authority_service.py
3. Route Phase 3 requests through authority_server.py
4. Remove placeholder authentication_layer.py
5. Use Phase 2's OS-observed client_pid for all authorization

---

## 6. NEXT STEPS

1. **R16C-1**: Implement real Windows caller identity verification
   - Either integrate with Phase 2 authority OR implement in authentication_layer.py
   
2. **R16C-2**: Establish authoritative subject registry bootstrap
   - Define who can register subjects
   - Integrate with authority_service.py
   
3. **R16C-3**: Verify HANDLE_LIST implementation
   - Test win32procthread import
   - Verify actual Windows API calls
   
4. **R16C-4**: Fix misleading/empty test coverage
   - Implement executable assertions for all tests
