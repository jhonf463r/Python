# P0.213 V5 Phase 2 Tool Metacognition Seed

## Windows Named Pipe

### Capability
Windows Named Pipe provides interprocess communication (IPC) with explicit security controls.

### Prerequisites
- Windows OS
- pywin32 library (win32file, win32pipe, win32security)
- Administrator privileges for DACL manipulation

### Side Effects
- Creates kernel-level IPC endpoint
- Persists until process termination
- Blocks on ConnectNamedPipe() until client connects

### Known Failures
1. **GetUserNameEx() not available**: win32security.GetUserNameEx() is not available in all pywin32 versions. Use win32api.GetUserName() or os.environ.get('USERNAME') instead.
2. **DACL setting may fail**: File permission restrictions may prevent DACL setting. Handle gracefully with try/except.
3. **Remote client rejection**: Must explicitly check for remote connections (not implemented in current version).

### Known Biases
1. **Local-only assumption**: Current implementation assumes local clients only. Remote client rejection is not fully implemented.
2. **Single-threaded server**: Current server loop is single-threaded per connection. May not scale for high concurrency.

### Independent Verification Strategy
1. Use Windows API (GetNamedPipeClientProcessId) to verify client identity
2. Do NOT trust JSON fields (pid, consumer_pid, sid) as authoritative
3. Verify DACL is set correctly using Windows security tools
4. Test with actual separate processes, not just threads

## AuthorityService

### Capability
AuthorityService provides the real security boundary by owning secret key, generation, and lease state.

### Prerequisites
- Persistent storage (file system)
- SQLite for persistent state
- Cryptographic library (secrets, hmac, hashlib)

### Side Effects
- Creates persistent files (secret.key, generation.txt, *.db)
- Modifies SQLite databases
- Generates real secret material

### Known Failures
1. **Secret key exposure**: If DACL fails, secret key may be readable by other users. Handle gracefully but log warning.
2. **SQLite locking**: Concurrent access to SQLite may cause locking issues. Use proper transaction handling.
3. **Generation mismatch**: If generation is incremented while client holds old lease, lease becomes invalid. This is intentional but may cause confusion.

### Known Biases
1. **Single-authority assumption**: Current implementation assumes single authority process. Multiple authorities would cause conflicts.
2. **Local filesystem assumption**: Current implementation uses local filesystem. Would need adaptation for distributed systems.

### Independent Verification Strategy
1. Verify secret key is 32 bytes (not placeholder)
2. Verify generation persists across restarts
3. Verify lease state persists across restarts
4. Verify consumed leases cannot be reused
5. Verify stale generation rejects old leases

## Process Identity API

### Capability
OS-derived process identity using psutil and Windows API.

### Prerequisites
- psutil library
- Windows API (win32pipe.GetNamedPipeClientProcessId)
- Process permissions

### Side Effects
- Queries OS process information
- May be blocked by security policies

### Known Failures
1. **PID reuse**: PID may be reused after process termination. Must verify create_time to detect reuse.
2. **Permission denied**: May not have permission to query certain process information. Handle gracefully.

### Known Biases
1. **Windows-only**: Current implementation is Windows-specific. Would need adaptation for Linux/macOS.
2. **Local-only**: Assumes local processes. Remote process identity is not handled.

### Independent Verification Strategy
1. Verify PID matches OS-observed PID
2. Verify create_time matches OS-observed create_time
3. Verify parent PID matches OS-observed parent PID
4. Test with actual process creation/termination

## Initial Metacognitive Rules

1. **JSON PID != OS identity**: Caller-supplied PID in JSON is NOT authoritative. Must use OS-derived identity (GetNamedPipeClientProcessId).
2. **Thread concurrency != Process concurrency**: threading.Lock is NOT interprocess exactly-once. Must use persistent state store with atomic operations.
3. **Process object != Authority**: Python process object is NOT a security boundary. Must use separate trusted authority process.
4. **Successful connection != Authorized client**: Successful Named Pipe connection does NOT imply authorized client. Must verify OS identity.
5. **Signed lease != Consumed lease**: HMAC-signed lease is NOT consumed. Must verify in persistent state store.
6. **API success != State transition proof**: API returning success does NOT prove state transition. Must verify in persistent state store.

## Lessons Learned

### Phase 1 vs Phase 2
- Phase 1: Data contract only (non-authoritative)
- Phase 2: Real security boundary (separate process)
- Do NOT confuse data model with authority
- Do NOT rely on in-process objects for security

### Secret Key Management
- Use secrets.token_bytes(32) for real secret material
- Store in OS-protected storage with DACL
- Persist across restarts
- Do NOT use placeholder values (b"placeholder")

### Atomic Operations
- Use SQLite UPDATE with WHERE clause for atomicity
- threading.Lock is NOT interprocess exactly-once
- dict.pop() is NOT interprocess exactly-once
- Must use persistent state store

### OS Identity
- Use GetNamedPipeClientProcessId for client identity
- Verify create_time to detect PID reuse
- Do NOT trust JSON fields as authoritative
- Verify parent-child relationship

### Protocol Design
- Keep protocol minimal (REGISTER_EXECUTION, ISSUE_LEASE, CONSUME_LEASE, VERIFY_EXECUTION, GET_STATUS)
- Use message framing (length header + body)
- Reject malformed messages
- Reject oversized messages

### Testing Strategy
- L1 CONTRACT: Protocol/schema tests
- L2 COMPONENT: Authority service behavior tests
- L3 REAL WINDOWS IPC: Real Named Pipe tests
- L4 MULTIPROCESS: Race, replay, PID reuse, stale generation, restart tests
- L5 ADVERSARIAL: Caller-supplied PID, forged scope, malformed IPC tests
- Primary proof for security invariants must be L3-L5
