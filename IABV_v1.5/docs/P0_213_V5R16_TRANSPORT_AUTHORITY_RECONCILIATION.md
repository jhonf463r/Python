# P0.213 V5 PHASE 3 — ROUND 16 TRANSPORT AUTHORITY RECONCILIATION

**Document Date**: 2026-08-22  
**Document Type**: Architectural Reconciliation  
**Purpose**: Reconcile Phase 3 with existing Phase 2 authenticated transport boundary

---

## 1. CURRENT ARCHITECTURE

### Phase 2 Authority System (Existing, Runtime Verified)

**Components**:
- `authority_server.py` - Windows Named Pipe server
- `authority_service.py` - Trusted authority process
- Pipe: `\\.\pipe\IABV_Authority`

**Transport Properties**:
- OS-authenticated IPC channel (Windows Named Pipe)
- Explicit DACL for access control
- OS-observed client PID via `GetNamedPipeClientProcessId`
- Bounded message size (1MB)
- Message framing with length headers
- Persistent connection mode
- JSON identity claims ignored (pid, sid fields in request data)

**Identity Verification**:
- Client PID obtained from Windows API: `win32pipe.GetNamedPipeClientProcessId(pipe_handle)`
- This PID is OS-derived and cannot be spoofed by the caller
- All authorization decisions use this OS-observed PID
- JSON fields like "pid" or "sid" in request data are explicitly ignored

**Authority Properties**:
- Real secret key (OS-protected storage)
- Canonical generation (persisted to file)
- Lease state store (SQLite)
- Run record store (SQLite)
- HMAC-SHA256 signatures for lease binding
- Atomic consumption with WHERE clause

**Protocol Handlers**:
- `REGISTER_EXECUTION` - Create canonical RunRecord
- `ISSUE_LEASE` - Issue HMAC-signed lease
- `CONSUME_LEASE` - Atomic verify+consume
- `VERIFY_EXECUTION` - Verify execution identity
- `GET_STATUS` - Return authority status

---

### Phase 3 Authority System (Current, Architecturally Flawed)

**Components**:
- `phase3_authority.py` - Phase 3 authority extension
- `authentication_layer.py` - Authentication layer
- Transport: None (accepts caller-supplied `client_pid`)

**Transport Properties**:
- NO verified transport binding
- Accepts `client_pid` as application-level parameter
- Accepts `execution_id` as application-level parameter
- No OS-verified peer identity

**Identity Verification**:
- `verify_caller_identity(client_pid)` - Uses pywin32 to verify SID of caller-supplied PID
- **CRITICAL FLAW**: The `client_pid` itself is caller-controlled
- Caller can supply any PID, and the system will verify that PID's SID
- This does NOT establish the identity of the actual calling connection

**Authority Properties**:
- Subject registry (SQLite)
- Join tokens (in-memory)
- Generation from Phase 2 (read-only)
- Lifecycle states (CREATED, ACTIVE, REVOKED)

**Protocol Handlers**:
- `REQUEST_JOIN` - Generate join token
- `REQUEST_CHALLENGE` - Request challenge
- `REDEEM_JOIN` - Redeem join token

---

## 2. EXACT TRUST-BOUNDARY GAP

### The Gap

Phase 3 has no verified transport binding. It accepts:

```text
caller-supplied client_pid
caller-supplied execution_id
```

as application-level parameters. Even though `verify_caller_identity()` uses pywin32 to verify the SID of the caller-supplied PID, the PID itself is not verified to be the actual calling connection.

### The Attack Model

An attacker can:

```text
1. Connect to Phase 3 authority
2. Supply client_pid = victim PID
3. Supply subject_id = victim subject
4. Supply public_key = victim key
5. Phase 3 verifies victim PID's SID (which is valid)
6. Phase 3 authorizes the request
```

This is PID spoofing. The actual calling connection is not verified.

### The Missing Property

The real missing property is:

```text
ACTUAL IPC PEER
        ↓
OS-VERIFIED PEER IDENTITY
        ↓
AUTHORIZED SUBJECT
        ↓
PHASE 3 AUTHORITY
```

Not:

```text
CALLER-SUPPLIED PID
        ↓
Phase3Authority
```

---

## 3. EXISTING PHASE 2 TRANSPORT

### Named Pipe Server

**File**: `src/iabv_v15/services/trust/authority_server.py`

**Properties**:
- Pipe name: `\\.\pipe\IABV_Authority`
- Pipe access: `PIPE_ACCESS_DUPLEX`
- Pipe type: `PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT`
- Security: Explicit DACL with actual process token SID
- Max instances: `PIPE_UNLIMITED_INSTANCES`

**Identity Verification**:
```python
client_pid = win32pipe.GetNamedPipeClientProcessId(pipe_handle)
```

This is OS-derived and cannot be spoofed.

**Request Routing**:
```python
response = self._route_request(request, client_pid)
```

The OS-observed `client_pid` is passed to all handlers.

**JSON Identity Claims Ignored**:
```python
# PART VIII: JSON identity claims are ignored
if 'pid' in request.get('data', {}):
    print(f"[AuthorityServer] WARNING: JSON contains 'pid' claim - IGNORED", flush=True)
if 'sid' in request.get('data', {}):
    print(f"[AuthorityServer] WARNING: JSON contains 'sid' claim - IGNORED", flush=True)
```

---

### Authority Service

**File**: `src/iabv_v15/services/trust/authority_service.py`

**Properties**:
- Real secret key (OS-protected storage)
- Canonical generation (persisted to file)
- Lease state store (SQLite)
- Run record store (SQLite)

**Authorization Decisions**:
All handlers use the OS-observed `client_pid` for authorization:

```python
def handle_register_execution(self, request: AuthorityRequest, client_pid: int) -> AuthorityResponse:
    # Uses client_pid for RunRecord creation
    
def handle_issue_lease(self, request: AuthorityRequest, client_pid: int) -> AuthorityResponse:
    # Verifies client_pid matches run record
    
def handle_consume_lease(self, request: AuthorityRequest, client_pid: int) -> AuthorityResponse:
    # Verifies client_pid matches run record
```

---

## 4. PHASE 3 CURRENT PATH

### Current Request Flow

```text
CLIENT PROCESS
      │
      │ (unverified connection)
      ▼
PHASE3_AUTHORITY
      │
      ├─ caller-supplied client_pid
      ├─ caller-supplied execution_id
      ├─ caller-supplied subject_id
      └─ caller-supplied public_key
      │
      ▼
verify_caller_identity(client_pid)
      │
      ├─ OpenProcessToken(client_pid)
      ├─ GetTokenInformation(client_pid)
      └─ Verify SID
      │
      ▼
validate_subject_key_binding(subject_id, public_key, caller_sid)
      │
      ▼
AUTHORIZATION DECISION
```

**Problem**: The `client_pid` is caller-controlled. Even though the SID verification is correct, the PID itself is not verified to be the actual calling connection.

---

## 5. TARGET ARCHITECTURE

### Required Integration

Phase 3 must become downstream of the Phase 2 authenticated transport boundary:

```text
CLIENT PROCESS
      │
      ▼
WINDOWS NAMED PIPE
      │
      ├─ \\.\pipe\IABV_Authority
      └─ Explicit DACL
      │
      ▼
AUTHORITY SERVER
      │
      ├─ GetNamedPipeClientProcessId
      └─ OS-observed client_pid
      │
      ▼
AUTHORITY SERVICE
      │
      ├─ Verify client_pid
      ├─ Canonical RunRecord lookup
      └─ Authorization decision
      │
      ▼
PHASE3 AUTHORITY (NEW HANDLER)
      │
      ├─ AuthenticatedPeer (from transport)
      ├─ subject_id (requested context)
      ├─ public_key (requested context)
      └─ execution_id (requested context)
      │
      ▼
SUBJECT REGISTRY RESOLUTION
      │
      ├─ AuthenticatedPeer.pid → authorized subject
      └─ AuthenticatedPeer.sid → subject SID verification
      │
      ▼
JOIN TOKEN GENERATION
```

### AuthenticatedPeer Object

Create an authenticated identity object from the transport layer:

```python
@dataclass
class AuthenticatedPeer:
    """OS-verified peer identity from transport layer."""
    process_id: int
    windows_sid: str
    parent_authority: int
    channel_id: str
    verified: bool = True
```

**Critical**: This object must be created by the trusted transport layer (Phase 2). It must NOT be constructible from untrusted JSON.

---

## 6. AUTHORITY OWNERSHIP

### Current Authority Owners

**Phase 2**:
- Secret key: AuthorityService process
- Generation: AuthorityService process
- Lease state: AuthorityService process
- Run records: AuthorityService process

**Phase 3** (Current):
- Subject registry: AuthenticationLayer (unverified)
- Join tokens: Phase3AuthorityExtension (unverified)

### Required Authority Owners

**Phase 2** (unchanged):
- Secret key: AuthorityService process
- Generation: AuthorityService process
- Lease state: AuthorityService process
- Run records: AuthorityService process

**Phase 3** (integrated):
- Subject registry: AuthorityService process (new)
- Join tokens: AuthorityService process (new)
- Phase 3 handler: Downstream of Phase 2 transport

---

## 7. IDENTITY DERIVATION

### Current Identity Derivation (Flawed)

```python
# Phase 3 current
client_pid = request.get('client_pid')  # Caller-supplied
caller_verified, caller_sid = self._auth_layer.verify_caller_identity(client_pid)
```

### Required Identity Derivation

```python
# Phase 2 transport
client_pid = win32pipe.GetNamedPipeClientProcessId(pipe_handle)  # OS-derived
# Derive SID from OS-observed PID
caller_sid = derive_sid_from_pid(client_pid)

# Create AuthenticatedPeer
peer = AuthenticatedPeer(
    process_id=client_pid,
    windows_sid=caller_sid,
    parent_authority=derive_parent_authority(client_pid),
    channel_id=pipe_handle,
    verified=True
)

# Pass to Phase 3 handler
response = phase3_handler.handle_request_join(request, peer)
```

---

## 8. SUBJECT REGISTRATION AUTHORITY

### Current Registration (Flawed)

```python
# Phase 3 current
def register_subject(
    self,
    subject_id: str,
    windows_sid: str,
    allowed_public_keys: list[str],
    parent_authority: str,
    registering_authority: str
):
    # No verification of registering_authority
    # Any Phase 3 caller can register subjects
```

**Problem**: `registering_authority` is a parameter but not verified. Any Phase 3 caller can register subjects.

### Required Registration Authority

Subject registration must be performed by the trusted authority process (Phase 2 AuthorityService), not by untrusted Phase 3 clients.

**Options**:
1. Add `REGISTER_SUBJECT` handler to AuthorityService
2. Use existing `REGISTER_EXECUTION` to implicitly register subjects
3. Create a separate bootstrap process with trusted authority

**WHO MAY REGISTER?**: AuthorityService process only
**WHO MAY REVOKE?**: AuthorityService process only
**WHO MAY MODIFY?**: AuthorityService process only
**WHO APPROVES PUBLIC KEY?**: AuthorityService process only
**WHO APPROVES WINDOWS SID?**: AuthorityService process only
**WHO APPROVES PARENT AUTHORITY?**: AuthorityService process only

---

## 9. JOIN STATE

### Current Join State (Flawed)

```python
# Phase 3 current
join_tokens: dict[str, dict] = {}  # In-memory
# No atomic uniqueness enforcement
# Multiple join tokens can be created for same subject_id + execution_id
```

**Problem**: No exactly-once semantics for join creation. Two calls can create two valid join tokens.

### Required Join State

Join state must be stored in the AuthorityService process with atomic uniqueness constraints.

**Database Schema**:
```sql
CREATE TABLE join_authorizations (
    join_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL,
    execution_id TEXT NOT NULL,
    generation INTEGER NOT NULL,
    client_pid INTEGER NOT NULL,
    created_at REAL NOT NULL,
    consumed INTEGER NOT NULL DEFAULT 0,
    UNIQUE(subject_id, execution_id, generation)
)
```

**Lifecycle**:
```text
NO_AUTHORIZATION
       ↓
PENDING (join created)
       ↓
CONSUMED (join redeemed)
```

**Atomic Enforcement**:
```sql
INSERT INTO join_authorizations (...)
VALUES (...)
ON CONFLICT(subject_id, execution_id, generation)
DO NOTHING
```

---

## 10. GENERATION BINDING

### Current Generation Binding

```python
# Phase 3 current
generation = self._get_current_generation()  # Reads from run_records.generation
```

Phase 3 reads generation from Phase 2's run_records database. This is correct.

### Required Generation Binding

Phase 3 must continue to use Phase 2's canonical generation. No change required.

---

## 11. PARENT AUTHORITY

### Current Parent Authority (Unused)

```python
# Verify parent authority using psutil
def verify_parent_authority(self, client_pid: int, expected_parent: str) -> bool:
    process = psutil.Process(client_pid)
    parent_pid = process.ppid()
    return str(parent_pid) == expected_parent
```

**Problem**: This method exists but is not called in the authorization path.

### Required Parent Authority

Parent authority must be enforced at the actual authorization boundary:

```python
# In Phase 2 transport
peer = AuthenticatedPeer(
    process_id=client_pid,
    windows_sid=caller_sid,
    parent_authority=derive_parent_authority(client_pid),  # Derive from OS
    channel_id=pipe_handle,
    verified=True
)

# In Phase 3 handler
if not verify_parent_authority(peer, subject.parent_authority):
    return {"success": False, "error": "Parent authority mismatch"}
```

---

## 12. FAILURE/RESTART BEHAVIOR

### Current Behavior

- Phase 2: Persistent state (SQLite, files)
- Phase 3: In-memory state (join tokens lost on restart)

### Required Behavior

- Phase 2: Persistent state (unchanged)
- Phase 3: Persistent state (join authorizations in SQLite)

---

## 13. NEGATIVE TEST STRATEGY

### Required Tests

1. **test_transport_identity_cannot_be_spoofed()**
   - Attack: Supply victim PID in client_pid field
   - Expected: REJECTED (OS-observed PID used instead)

2. **test_invalid_parent_authority_rejected()**
   - Attack: Connect from process with wrong parent
   - Expected: REJECTED

3. **test_double_join_rejected()**
   - Attack: Two sequential join requests for same subject_id + execution_id
   - Expected: Second request rejected

4. **test_concurrent_join_rejected()**
   - Attack: Parallel join requests for same subject_id + execution_id
   - Expected: Exactly one authorization, others rejected

5. **test_unauthorized_subject_registration_rejected()**
   - Attack: Attempt to register subject from untrusted client
   - Expected: REJECTED (only AuthorityService can register)

---

## 14. IMPLEMENTATION PLAN

### Step 1: Add Phase 3 Handler to AuthorityService

Add new handler to `authority_service.py`:
```python
def handle_phase3_request_join(
    self,
    request: AuthorityRequest,
    client_pid: int
) -> AuthorityResponse:
    """Handle Phase 3 REQUEST_JOIN with OS-verified peer identity."""
    # Create AuthenticatedPeer from OS-observed client_pid
    peer = self._create_authenticated_peer(client_pid)
    
    # Resolve subject from peer identity
    subject = self._resolve_subject(peer, request.data['subject_id'])
    
    # Generate join token with atomic uniqueness
    join_token = self._create_join_authorization(peer, subject, request.data['execution_id'])
    
    return AuthorityResponse(success=True, data={"join_token": join_token})
```

### Step 2: Add Join Authorization Table

Add to `authority_service.py`:
```python
def _init_join_authorization_db(self) -> None:
    conn = sqlite3.connect(str(self._join_auth_db))
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS join_authorizations (
            join_id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            execution_id TEXT NOT NULL,
            generation INTEGER NOT NULL,
            client_pid INTEGER NOT NULL,
            created_at REAL NOT NULL,
            consumed INTEGER NOT NULL DEFAULT 0,
            UNIQUE(subject_id, execution_id, generation)
        )
    """)
    
    conn.commit()
    conn.close()
```

### Step 3: Add Subject Registration Handler

Add to `authority_service.py`:
```python
def handle_register_subject(
    self,
    request: AuthorityRequest,
    client_pid: int
) -> AuthorityResponse:
    """Handle subject registration (authority-only)."""
    # Verify caller is authorized to register subjects
    # This should be restricted to trusted bootstrap process
    pass
```

### Step 4: Update Phase 3 to Use Transport

Modify `phase3_authority.py` to accept `AuthenticatedPeer` instead of `client_pid`:
```python
def handle_request_join(
    self,
    request_data: dict[str, Any],
    peer: AuthenticatedPeer  # Changed from client_pid
) -> dict[str, Any]:
    # Use peer.process_id, peer.windows_sid, peer.parent_authority
    pass
```

### Step 5: Update Authority Server Routing

Add to `authority_server.py`:
```python
handlers = {
    # Existing handlers
    "REGISTER_EXECUTION": self._authority.handle_register_execution,
    "ISSUE_LEASE": self._authority.handle_issue_lease,
    "CONSUME_LEASE": self._authority.handle_consume_lease,
    "VERIFY_EXECUTION": self._authority.handle_verify_execution,
    "GET_STATUS": self._authority.handle_get_status,
    # New Phase 3 handlers
    "PHASE3_REQUEST_JOIN": self._authority.handle_phase3_request_join,
}
```

---

## 15. MISSING AUTHORITATIVE REGISTRATION PATH

**Current State**: No authoritative subject registration path exists.

**Required Action**: STOP implementation and report `MISSING_AUTHORITATIVE_REGISTRATION_PATH`.

**Options**:
1. Create bootstrap process that runs before Phase 3 and registers subjects via AuthorityService
2. Integrate subject registration into existing `REGISTER_EXECUTION` flow
3. Use Phase 2's RunRecord as the authoritative subject registry

**Decision**: Use Phase 2's RunRecord as the authoritative subject registry. This avoids creating a new registration mechanism and leverages existing authoritative infrastructure.

---

## 16. FINAL ARCHITECTURE

### Single Authority

After integration, there will be one source of truth for:

- Caller identity: Phase 2 AuthorityService (OS-observed PID)
- Subject authority: Phase 2 AuthorityService (RunRecord)
- Parent authority: Phase 2 AuthorityService (derived from OS)
- Generation: Phase 2 AuthorityService (canonical)
- Join state: Phase 2 AuthorityService (persistent)
- Revocation: Phase 2 AuthorityService (generation increment)

### No parallel authorities

No parallel:
- RAM identity registry
- Phase 3 authority registry
- IPC identity registry

Derived views are allowed. Multiple authoritative decision-makers are not.

---

## 17. CONCLUSION

The root cause of R16-F1 (PID spoofing) is that Phase 3 has no verified transport binding. The solution is to integrate Phase 3 as a downstream handler of the existing Phase 2 authenticated transport boundary.

Phase 2 already has:
- OS-authenticated IPC channel (Windows Named Pipe)
- OS-observed client PID via `GetNamedPipeClientProcessId`
- Trusted authority process owning secret key and generation
- Persistent state stores (SQLite)

Phase 3 must:
- Accept `AuthenticatedPeer` from Phase 2 transport
- Use Phase 2's RunRecord as authoritative subject registry
- Store join authorizations in Phase 2's persistent store
- Enforce parent authority at the authorization boundary
- Implement exactly-once join creation with atomic constraints

**Status**: READY FOR IMPLEMENTATION
