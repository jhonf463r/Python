# P0.213 V5 PHASE 3 — ROUND 16 REMEDIATION DESIGN

**Design Date**: 2026-08-22  
**Design Type**: Security Remediation Architecture  
**Based On**: P0_213_V5R16_CRITICAL_FINDINGS_ROOT_CAUSE_REPORT.md  
**Target**: Independent adversarial re-audit readiness

---

## EXECUTIVE SUMMARY

This design specifies exact remediation for the 4 findings identified by Claude's independent audit:

1. **R16B-1 — Missing Authentication Boundary**
2. **R16B-2 — HANDLE_LIST Implementation**
3. **R16B-3 — Generation Authority Unification**
4. **R16B-4 — Bundle Integrity Correction**

The design follows the canonical architecture chain:
```
V5 Trust Boundary
    ↓
Round 15 authoritative state
    ↓
Phase 3 authorization
    ↓
join
    ↓
proof-of-possession
    ↓
generation
    ↓
controlled spawn
    ↓
execution
```

---

## SECTION A — CALLER AUTHENTICATION (R16B-1 REMEDIATION)

### Current Problem

**Missing Boundary**: No authentication layer between untrusted caller and `Phase3AuthorityExtension`

**Current Flow**:
```
Untrusted Caller
    ↓
RequestJoinRequest(subject_id, public_key) [caller-controlled]
    ↓
Phase3AuthorityExtension.handle_request_join
    ↓
Direct insertion into database
```

### Target Architecture

**Required Boundary**: Authentication/Authorization layer

**Target Flow**:
```
Untrusted Caller
    ↓
[NEW] Authentication Layer
    ↓
OS Identity Verification
    ↓
AuthorizationSubject Validation
    ↓
Subject → Public Key Binding
    ↓
Parent Authority Verification
    ↓
Phase3AuthorityExtension.handle_request_join
    ↓
Authorized insertion into database
```

### A.1 OS Identity Verification

**Requirement**: Verify caller's OS identity before accepting any request

**Implementation**: Windows Named Pipe client identity verification

**Design**:
```python
class AuthenticationLayer:
    def verify_caller_identity(self, client_pid: int) -> bool:
        """Verify caller's OS identity using Windows security API.
        
        Returns:
            True if caller identity is verified, False otherwise
        """
        # 1. Get process token for client_pid
        # 2. Verify token is valid
        # 3. Extract user SID from token
        # 4. Verify SID matches expected authorized user
        # 5. Return True only if all checks pass
```

**Security Properties**:
- Caller cannot forge OS identity
- PID alone is insufficient (must verify token)
- Only authorized Windows users can call Authority

### A.2 AuthorizationSubject Registry

**Requirement**: Pre-authorized AuthorizationSubject registry

**Design**:
```sql
CREATE TABLE authorized_subjects (
    subject_id TEXT PRIMARY KEY,
    windows_sid TEXT NOT NULL,
    allowed_public_keys TEXT NOT NULL,  -- JSON array of allowed keys
    parent_authority TEXT NOT NULL,     -- Parent process authority
    created_at REAL NOT NULL,
    revoked_at REAL,
    is_active INTEGER NOT NULL DEFAULT 1
);
```

**Invariants**:
- Only pre-registered subjects can request join
- Each subject bound to specific Windows SID
- Each subject has list of allowed public keys
- Revoked subjects cannot join

### A.3 Subject → Public Key Binding

**Requirement**: Validate that `subject_id` → `public_key` binding is authorized

**Design**:
```python
class AuthenticationLayer:
    def validate_subject_key_binding(
        self,
        subject_id: str,
        public_key: str,
        caller_sid: str
    ) -> bool:
        """Validate that subject_id and public_key are authorized for caller.
        
        Returns:
            True if binding is authorized, False otherwise
        """
        # 1. Lookup subject in authorized_subjects
        # 2. Verify subject.is_active == 1
        # 3. Verify subject.windows_sid == caller_sid
        # 4. Parse subject.allowed_public_keys JSON array
        # 5. Verify public_key is in allowed list
        # 6. Return True only if all checks pass
```

**Security Properties**:
- Caller cannot choose arbitrary subject_id
- Caller cannot choose arbitrary public_key
- Only pre-registered bindings are allowed

### A.4 Parent Authority Verification

**Requirement**: Verify parent process authority relationship

**Design**:
```python
class AuthenticationLayer:
    def verify_parent_authority(
        self,
        client_pid: int,
        parent_authority: str
    ) -> bool:
        """Verify that caller has required parent authority.
        
        Returns:
            True if parent authority is verified, False otherwise
        """
        # 1. Get parent PID of client_pid
        # 2. Verify parent PID matches expected parent_authority
        # 3. Verify parent process is authorized Authority process
        # 4. Return True only if all checks pass
```

**Security Properties**:
- Only authorized parent processes can spawn children
- Prevents unauthorized parent processes from using Authority

### A.5 Authentication Layer Integration

**Integration Point**: Before `Phase3AuthorityExtension.handle_request_join`

**Design**:
```python
class Phase3AuthorityExtension:
    def __init__(self, storage_root: str, generation: int):
        # ... existing init ...
        self._auth_layer = AuthenticationLayer()
    
    def handle_request_join(
        self,
        request_data: dict[str, Any],
        client_pid: int
    ) -> dict[str, Any]:
        # NEW: Authentication first
        if not self._auth_layer.verify_caller_identity(client_pid):
            return {"success": False, "error": "Caller identity verification failed"}
        
        # NEW: Subject validation
        if not self._auth_layer.validate_subject_key_binding(
            request.subject_id,
            request.public_key,
            caller_sid
        ):
            return {"success": False, "error": "Subject/key binding not authorized"}
        
        # NEW: Parent authority verification
        if not self._auth_layer.verify_parent_authority(
            client_pid,
            parent_authority
        ):
            return {"success": False, "error": "Parent authority verification failed"}
        
        # Proceed with existing logic
        request = RequestJoinRequest.from_dict(request_data)
        # ... rest of existing implementation ...
```

---

## SECTION B — GENERATION AUTHORITY UNIFICATION (R16B-3 REMEDIATION)

### Current Problem

**Divergent Sources**: 
- Design requires: `run_records.generation` (canonical)
- Implementation uses: `Phase3AuthorityExtension._generation` (independent)

### Target Architecture

**Single Source**: `run_records.generation` as sole authoritative source

### B.1 Remove Independent Generation

**Change**: Remove `generation` parameter from `Phase3AuthorityExtension.__init__`

**Before**:
```python
def __init__(self, storage_root: str, generation: int):
    self._generation = generation
```

**After**:
```python
def __init__(self, storage_root: str, db_connection: sqlite3.Connection):
    self._storage_root = Path(storage_root)
    self._db_connection = db_connection  # Connection to run_records DB
    # Remove self._generation
```

### B.2 Read Canonical Generation

**Change**: Read generation from `run_records.generation` database

**Design**:
```python
class Phase3AuthorityExtension:
    def _get_current_generation(self, execution_id: str) -> int:
        """Read canonical generation from run_records.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Current generation from run_records.generation
        """
        cursor = self._db_connection.cursor()
        cursor.execute("""
            SELECT generation
            FROM run_records
            WHERE execution_id = ?
        """, (execution_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Execution {execution_id} not found")
        
        return row[0]
```

### B.3 Use Canonical Generation Everywhere

**Change**: Replace all `self._generation` with `self._get_current_generation(execution_id)`

**Locations to Update**:
1. Line 140: `self._generation` → `self._get_current_generation(execution_id)`
2. Line 213: `if generation != self._generation` → `if generation != self._get_current_generation(execution_id)`
3. Line 239: `self._generation` → `self._get_current_generation(execution_id)`
4. Line 312: `if generation != self._generation` → `if generation != self._get_current_generation(execution_id)`
5. Line 378: `self._generation` → `self._get_current_generation(execution_id)`

### B.4 Add execution_id Parameter

**Change**: All methods need `execution_id` parameter to read canonical generation

**Design**:
```python
def handle_request_join(
    self,
    request_data: dict[str, Any],
    client_pid: int,
    execution_id: str  # NEW parameter
) -> dict[str, Any]:
    generation = self._get_current_generation(execution_id)
    # ... use generation instead of self._generation ...
```

### B.5 Generation Invariant Enforcement

**Invariant**: `run_records.generation = THE generation for that execution`

**Enforcement**:
- Phase 3 never writes to generation field
- Phase 3 only reads from generation field
- Generation changes only through Round 15 atomic recovery transaction
- No secondary generation registry exists

---

## SECTION C — HANDLE INHERITANCE CORRECTION (R16B-2 REMEDIATION)

### Current Problem

**Global Inheritance**: `bInheritHandles=True` allows all inheritable handles to be inherited

**Current Code**:
```python
si = win32process.STARTUPINFO()
# ...
security_attributes.bInheritHandle = True
result = win32process.CreateProcess(..., True, ...)
```

### Target Architecture

**Explicit Handle List**: Only stdin read handle is inheritable

### C.1 Use STARTUPINFOEX

**Change**: Replace `STARTUPINFO` with `STARTUPINFOEX`

**Design**:
```python
import ctypes
import win32procthread

# Initialize extended startup info
si = win32process.STARTUPINFOEX()
si.StartupInfo.cb = ctypes.sizeof(si)
```

### C.2 Create Attribute List

**Change**: Initialize process thread attribute list

**Design**:
```python
# Create attribute list for 1 attribute
attribute_list_size = win32procthread.InitializeProcThreadAttributeList(1)
attribute_list = ctypes.create_string_buffer(attribute_list_size)
si.lpAttributeList = attribute_list
```

### C.3 Set Handle List Attribute

**Change**: Set `PROC_THREAD_ATTRIBUTE_HANDLE_LIST` with explicit handle list

**Design**:
```python
# Define handle list (only stdin read handle)
handle_list = [read_handle]

# Convert to ctypes array
handle_array = (ctypes.c_void_p * len(handle_list))()
for i, handle in enumerate(handle_list):
    handle_array[i] = handle

# Update attribute
win32procthread.UpdateProcThreadAttribute(
    attribute_list,
    0,
    win32procthread.PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
    handle_array,
    ctypes.sizeof(ctypes.c_void_p) * len(handle_list)
)
```

### C.4 Create Process with Attribute List

**Change**: Create process using extended startup info

**Design**:
```python
result = win32process.CreateProcess(
    None,
    full_command,
    security_attributes,
    None,
    True,  # bInheritHandles still TRUE but restricted by attribute list
    win32process.CREATE_NEW_PROCESS_GROUP,
    None,
    working_directory,
    si  # STARTUPINFOEX with attribute list
)
```

### C.5 Cleanup Attribute List

**Change**: Clean up attribute list after spawn

**Design**:
```python
# After successful spawn
win32procthread.DeleteProcThreadAttributeList(attribute_list)
```

### C.6 Security Properties

**Guarantees**:
- Only stdin read handle is inheritable
- All other inheritable handles are NOT inherited
- Explicit handle list prevents accidental inheritance
- Child cannot access parent's unrelated handles

---

## SECTION D — REVOCATION INTEGRATION (ROUND 15 COMPLIANCE)

### Round 15 Revocation Model

**State Machine**:
```
UNPREPARED
    ↓
PREPARING
    ↓
PREPARED
    ↓
FAILED_PREPARATION
    ↓
REQUIRES_NEW_AUTHORIZATION (revocation)
    ↓
UNPREPARED (next generation)
```

### D.1 Revocation on Failed Preparation

**Requirement**: Atomic revocation when preparation fails

**Design**:
```python
class Phase3AuthorityExtension:
    def revoke_failed_preparation(
        self,
        execution_id: str,
        generation: int
    ) -> bool:
        """Revoke all capabilities for failed generation.
        
        This implements Round 15 atomic recovery:
        - Revoke all capabilities for generation N
        - Advance to generation N+1
        - Clear pinned_public_key
        - Set state to REQUIRES_NEW_AUTHORIZATION
        
        Args:
            execution_id: Execution identifier
            generation: Failed generation
            
        Returns:
            True if revocation succeeded, False otherwise
        """
        conn = self._db_connection.cursor()
        
        try:
            conn.execute("BEGIN IMMEDIATE")
            
            # 1. Revoke all capabilities for generation
            conn.execute("""
                UPDATE broker_capabilities
                SET status = 'REVOKED',
                    revoked_at = ?
                WHERE execution_id = ?
                  AND generation = ?
                  AND status IN ('PENDING', 'CONSUMED')
            """, (time.time(), execution_id, generation))
            
            # 2. Revoke all join tokens for generation
            conn.execute("""
                UPDATE join_tokens
                SET redeemed = 1,
                    revoked_at = ?
                WHERE execution_id = ?
                  AND generation = ?
                  AND redeemed = 0
            """, (time.time(), execution_id, generation))
            
            # 3. Atomic generation advance
            conn.execute("""
                UPDATE run_records
                SET generation = generation + 1,
                    child_authorization_state = 'REQUIRES_NEW_AUTHORIZATION',
                    pinned_public_key = NULL,
                    child_authorization_generation = generation + 1
                WHERE execution_id = ?
                  AND generation = ?
                  AND child_authorization_state = 'FAILED_PREPARATION'
            """, (execution_id, generation))
            
            conn.execute("COMMIT")
            return True
            
        except Exception as e:
            conn.execute("ROLLBACK")
            raise
```

### D.2 Revocation on Child Crash

**Requirement**: Revoke authorization if child crashes before successful join

**Design**:
```python
class Phase3AuthorityExtension:
    def revoke_crashed_child(
        self,
        execution_id: str,
        generation: int,
        child_pid: int
    ) -> bool:
        """Revoke authorization for crashed child.
        
        Args:
            execution_id: Execution identifier
            generation: Current generation
            child_pid: Crashed child PID
            
        Returns:
            True if revocation succeeded, False otherwise
        """
        # Similar to revoke_failed_preparation
        # But specific to child crash scenario
        # Mark join_token as revoked due to crash
```

### D.3 Revocation on Broker Crash

**Requirement**: Handle broker crash scenarios

**Design**:
```python
class Phase3AuthorityExtension:
    def revoke_broker_crash(
        self,
        execution_id: str,
        generation: int
    ) -> bool:
        """Revoke authorization after broker crash.
        
        Args:
            execution_id: Execution identifier
            generation: Current generation
            
        Returns:
            True if revocation succeeded, False otherwise
        """
        # Revoke all pending capabilities
        # Advance generation
        # Require new authorization
```

---

## SECTION E — NEGATIVE SECURITY TESTS

### E.1 Forged subject_id Test

**Objective**: Verify that forged subject_id is rejected

**Design**:
```python
def test_forged_subject_id_rejected():
    """Test that unauthorized subject_id is rejected."""
    # 1. Register subject A with allowed public key X
    # 2. Attempt REQUEST_JOIN with subject_id B (unregistered)
    # 3. Verify request is rejected
    # 4. Verify error message indicates unauthorized subject
```

### E.2 Forged public_key Test

**Objective**: Verify that forged public_key is rejected

**Design**:
```python
def test_forged_public_key_rejected():
    """Test that unauthorized public_key is rejected."""
    # 1. Register subject A with allowed public key X
    # 2. Attempt REQUEST_JOIN with public_key Y (not in allowed list)
    # 3. Verify request is rejected
    # 4. Verify error message indicates unauthorized key
```

### E.3 Unauthorized Caller Test

**Objective**: Verify that unauthorized caller is rejected

**Design**:
```python
def test_unauthorized_caller_rejected():
    """Test that unauthorized Windows user is rejected."""
    # 1. Attempt REQUEST_JOIN from unauthorized Windows SID
    # 2. Verify request is rejected
    # 3. Verify error message indicates unauthorized caller
```

### E.4 Wrong Parent Test

**Objective**: Verify that wrong parent process is rejected

**Design**:
```python
def test_wrong_parent_rejected():
    """Test that unauthorized parent process is rejected."""
    # 1. Attempt REQUEST_JOIN from unauthorized parent PID
    # 2. Verify request is rejected
    # 3. Verify error message indicates unauthorized parent
```

### E.5 Handle Inheritance Negative Test

**Objective**: Verify that unrelated handles are not inherited

**Design**:
```python
def test_unrelated_handle_not_inherited():
    """Test that unrelated inheritable handle is not inherited."""
    # 1. Create unrelated inheritable handle in parent
    # 2. Spawn child with HANDLE_LIST (only stdin)
    # 3. Child attempts to access unrelated handle
    # 4. Verify access fails (handle not inherited)
    # 5. Verify only stdin handle is available
```

**Platform Note**: Windows-specific test. Document Linux limitation.

### E.6 Cross-Run Token Test

**Objective**: Verify that token from different run is rejected

**Design**:
```python
def test_cross_run_token_rejected():
    """Test that token from different execution is rejected."""
    # 1. Create token for execution A, generation N
    # 2. Attempt to redeem token for execution B
    # 3. Verify redemption is rejected
    # 4. Verify error indicates cross-run token
```

### E.7 Replayed Token Test

**Objective**: Verify that replayed token is rejected

**Design**:
```python
def test_replayed_token_rejected():
    """Test that already-redeemed token is rejected."""
    # 1. Create and redeem token
    # 2. Attempt to redeem same token again
    # 3. Verify redemption is rejected
    # 4. Verify error indicates already redeemed
```

### E.8 Stale Generation Test

**Objective**: Verify that stale generation is rejected

**Design**:
```python
def test_stale_generation_rejected():
    """Test that token from old generation is rejected."""
    # 1. Create token for generation N
    # 2. Advance to generation N+1
    # 3. Attempt to redeem token from generation N
    # 4. Verify redemption is rejected
    # 5. Verify error indicates generation mismatch
```

---

## SECTION F — BUNDLE INTEGRITY CORRECTION (R16B-4 REMEDIATION)

### F.1 Exclude pycache from Bundle

**Change**: Update bundle creation script to exclude `__pycache__` directories

**Design**:
```python
# In bundle creation script
import os

def should_exclude_file(file_path: str) -> bool:
    """Determine if file should be excluded from bundle."""
    # Exclude __pycache__ directories
    if '__pycache__' in file_path:
        return True
    # Exclude .pyc files
    if file_path.endswith('.pyc'):
        return True
    return False
```

### F.2 Regenerate Manifest

**Change**: Regenerate manifest with correct file count (22 files)

**Design**:
```python
# Re-run compute_bundle_hashes.py with exclusion logic
# Verify output shows exactly 22 files
```

### F.3 Update Report

**Change**: Update report with correct verification results

**Design**:
```markdown
## I. UNEXPECTED FILES

**Expected Files**: 22 (from manifest)  
**Actual Files in Bundle**: 22  
**Unexpected Files**: 0  
**Status**: PASS
```

---

## SECTION G — IMPLEMENTATION SEQUENCE

### Phase 1: Architecture Documentation
1. ✅ Root Cause Report
2. ✅ Remediation Design (this document)
3. ⏳ Before/After Architecture

### Phase 2: Implementation
4. Implement Authentication Layer
5. Implement AuthorizationSubject Registry
6. Update Phase3AuthorityExtension with authentication
7. Remove independent generation from Phase3AuthorityExtension
8. Implement canonical generation reading
9. Implement HANDLE_LIST in child_spawn.py
10. Implement revocation methods
11. Update bundle creation script

### Phase 3: Testing
12. Implement negative security tests
13. Run full test suite
14. Verify all tests pass

### Phase 4: Verification
15. Regenerate audit bundle (corrected)
16. Independent adversarial re-audit by Claude

---

## SECTION H — SUCCESS CRITERIA

### H.1 Authentication
- ✅ OS identity verified before any request
- ✅ AuthorizationSubject registry exists
- ✅ Subject → public key binding validated
- ✅ Parent authority verified
- ✅ Unauthorized callers rejected

### H.2 Generation Authority
- ✅ Single source: run_records.generation
- ✅ Phase 3 reads from canonical source
- ✅ No independent generation field
- ✅ Generation invariant enforced

### H.3 Handle Inheritance
- ✅ STARTUPINFOEX used
- ✅ PROC_THREAD_ATTRIBUTE_HANDLE_LIST set
- ✅ Only stdin handle in list
- ✅ Unrelated handles not inherited

### H.4 Revocation
- ✅ Failed preparation triggers revocation
- ✅ Child crash triggers revocation
- ✅ Broker crash triggers revocation
- ✅ Atomic revocation transaction

### H.5 Testing
- ✅ All negative security tests implemented
- ✅ All negative tests pass
- ✅ Full test suite passes

### H.6 Bundle Integrity
- ✅ No __pycache__ in bundle
- ✅ Manifest matches actual contents
- ✅ Report verification accurate

---

## FINAL VERDICT

**P0_213_V5R16_REMEDIATION_DESIGN_COMPLETE**

This design provides exact remediation specifications for all 4 findings. Implementation may proceed after Before/After Architecture documentation is complete.
