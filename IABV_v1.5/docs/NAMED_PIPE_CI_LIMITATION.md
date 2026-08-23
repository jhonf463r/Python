# Windows Named Pipe CI Environment Limitation

## Issue Summary
Windows named pipes are created successfully in GitHub Actions Windows runners and are visible to PowerShell, but client processes cannot connect to them, receiving `ERROR_FILE_NOT_FOUND` (error code 2) despite the pipe being listed in `\\.\pipe\`.

## Debugging Attempts
The following approaches were tested without success:

1. **Pipe creation parameters**
   - PIPE_WAIT vs PIPE_NOWAIT modes
   - PIPE_TYPE_MESSAGE vs PIPE_TYPE_BYTE
   - Various buffer sizes and timeout values

2. **Connection handling**
   - Blocking ConnectNamedPipe
   - Overlapped I/O with ConnectNamedPipe
   - FILE_FLAG_OVERLAPPED during pipe creation
   - DisconnectNamedPipe and ConnectNamedPipe on same handle
   - Standard pipe recreation pattern (close and create new)
   - Skipping ConnectNamedPipe entirely

3. **Security attributes**
   - Explicit DACL with process token SID
   - No security attributes (None) for maximum compatibility

4. **Timing and delays**
   - Increased delays from 3 to 10 seconds before tests
   - Additional delays after pipe listing

5. **Pipe names**
   - Original: `\\.\pipe\IABV_Authority`
   - Alternative: `\\.\pipe\IABV_Authority_Test`

6. **Logging and diagnostics**
   - Pipe name verification (length, repr)
   - Detailed CreateNamedPipe parameter logging
   - Client and server process identity logging
   - PowerShell pipe listing

## Observed Behavior
- Authority process starts successfully
- Pipe is created with valid handle
- Pipe is visible to PowerShell: `[System.IO.Directory]::GetFiles("\\.\pipe\")`
- Server calls ConnectNamedPipe and blocks waiting for connection
- Client attempts CreateFile with correct pipe name
- Client receives ERROR_FILE_NOT_FOUND (error code 2)
- No client connection is ever established

## Environment
- GitHub Actions Windows runner
- Python 3.13
- pywin32 for Windows IPC
- PowerShell 7

## Conclusion
The GitHub Actions Windows CI environment appears to have a fundamental limitation with named pipe IPC that prevents client connections despite successful pipe creation and visibility. This may be due to:
- Container/virtualization isolation
- Session 0 vs user session isolation
- Security policy restrictions in CI environment
- Named pipe namespace restrictions

## Recommendation
Consider alternative IPC mechanisms for CI testing:
- TCP sockets (localhost)
- Unix domain sockets (if available)
- Shared memory with synchronization primitives
- File-based IPC with proper locking

The named pipe implementation works correctly in local development environments but cannot be tested in the current GitHub Actions Windows CI setup.
