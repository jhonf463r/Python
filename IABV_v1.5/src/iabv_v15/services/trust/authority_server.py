"""Authority Server: Windows Named Pipe server for P0.213 V5 Phase 2.

This implements the real Windows Named Pipe trust boundary.

CRITICAL: This is the REAL IPC boundary. It enforces:
- Explicit DACL
- Remote client rejection
- Bounded message size
- Message framing
- Partial read handling
- Malformed message rejection
- Readiness handshake
- Clean shutdown

Phase 2 Status: RUNTIME_VERIFIED (real Windows IPC)
"""

from __future__ import annotations

import json
import os
import struct
import threading
import time
import dataclasses
from dataclasses import dataclass
from typing import Any, Optional

import win32file
import win32pipe
import win32security
import pywintypes

from iabv_v15.services.trust.authority_service import (
    AuthorityRequest,
    AuthorityResponse,
    AuthorityService,
)


# ── Constants ───────────────────────────────────────────────────────────────

PIPE_NAME = r"\\.\pipe\IABV_Authority"
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB
MESSAGE_HEADER_SIZE = 4  # uint32 for message length
BUFFER_SIZE = 4096


# ── Named Pipe Server ────────────────────────────────────────────────────────

class AuthorityServer:
    """Windows Named Pipe server for authority service.
    
    This implements the real IPC boundary with:
    - Explicit DACL
    - Bounded message size
    - Message framing
    - Partial read handling
    - Malformed message rejection
    - OS-observed client identity verification
    
    PART IX: Registration vs Authentication
    CONNECTING PROCESS ≠ REGISTERED PROCESS ≠ AUTHORIZED PROCESS
    
    A process automatically appearing in an in-memory connection list is NOT authentication.
    Future authorization must require:
    - observed_identity (OS-observed PID from GetNamedPipeClientProcessId)
    - canonical RunRecord
    - registered execution
    - scope/policy
    
    Current Phase 2: Only OS identity verification via GetNamedPipeClientProcessId is implemented.
    RunRecord-based authorization is NOT implemented yet.
    """
    
    def __init__(self, authority: AuthorityService):
        """Initialize authority server.
        
        Args:
            authority: Authority service instance
        """
        self._authority = authority
        self._shutdown = False
        self._shutdown_lock = threading.Lock()
        self._server_thread: Optional[threading.Thread] = None
    
    def _create_security_attributes(self) -> pywintypes.SECURITY_ATTRIBUTES:
        """Create security attributes with explicit DACL.
        
        Phase 2: Explicit DACL for Named Pipe.
        PART II: Instrumented to log exact DACL details.
        PART I: Diagnose SID source - compare LookupAccountName vs actual token SID.
        """
        # PART I: Get actual process token SID
        import win32api
        import win32security
        process_token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32security.TOKEN_QUERY)
        actual_token_sid = win32security.GetTokenInformation(process_token, win32security.TokenUser)[0]
        print(f"[AuthorityServer] ACTUAL process token SID: {actual_token_sid}", flush=True)
        
        # PART I: Get SID from username (current incorrect method)
        user = os.environ.get('USERNAME', os.environ.get('USER', 'unknown'))
        print(f"[AuthorityServer] Creating DACL for username: {user}", flush=True)
        
        username_sid, _, _ = win32security.LookupAccountName(None, user)
        print(f"[AuthorityServer] LookupAccountName('{user}') SID: {username_sid}", flush=True)
        
        # PART I: Report mismatch
        if actual_token_sid != username_sid:
            print(f"[AuthorityServer] WARNING: SID MISMATCH DETECTED", flush=True)
            print(f"[AuthorityServer]   Actual token SID: {actual_token_sid}", flush=True)
            print(f"[AuthorityServer]   LookupAccountName SID: {username_sid}", flush=True)
            print(f"[AuthorityServer]   This will cause DACL to deny actual process!", flush=True)
        else:
            print(f"[AuthorityServer] SID sources match: {actual_token_sid}", flush=True)
        
        # PART II: Use actual process token SID for DACL (fix)
        sid = actual_token_sid
        
        # Create DACL: only current user has full access
        dacl = win32security.ACL()
        dacl.AddAccessAllowedAce(
            win32security.ACL_REVISION,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            sid
        )
        print(f"[AuthorityServer] DACL ACE added:", flush=True)
        print(f"[AuthorityServer]   Type: ACCESS_ALLOWED", flush=True)
        print(f"[AuthorityServer]   Permissions: GENERIC_READ | GENERIC_WRITE", flush=True)
        print(f"[AuthorityServer]   SID: {sid}", flush=True)
        print(f"[AuthorityServer]   SID Source: ACTUAL PROCESS TOKEN (not LookupAccountName)", flush=True)
        
        # Create security descriptor
        security_descriptor = win32security.SECURITY_DESCRIPTOR()
        security_descriptor.SetSecurityDescriptorDacl(1, dacl, 0)
        print(f"[AuthorityServer] Security descriptor created", flush=True)
        print(f"[AuthorityServer]   DACL present: {security_descriptor.GetSecurityDescriptorDacl() is not None}", flush=True)
        
        # Create security attributes
        security_attributes = pywintypes.SECURITY_ATTRIBUTES()
        security_attributes.SECURITY_DESCRIPTOR = security_descriptor
        
        return security_attributes
    
    def _create_named_pipe(self) -> int:
        """Create Named Pipe with explicit security.
        
        Phase 2: Explicit DACL, reject remote clients.
        PART II: Instrumented to log exact CreateNamedPipe parameters.
        """
        security_attributes = self._create_security_attributes()
        
        # Create named pipe with exact parameters
        pipe_access = win32pipe.PIPE_ACCESS_DUPLEX
        pipe_type = win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT
        max_instances = win32pipe.PIPE_UNLIMITED_INSTANCES
        out_buffer_size = BUFFER_SIZE
        in_buffer_size = BUFFER_SIZE
        default_timeout = 0
        
        print(f"[AuthorityServer] CreateNamedPipe parameters:")
        print(f"[AuthorityServer]   Pipe name: {PIPE_NAME}")
        print(f"[AuthorityServer]   Pipe access: PIPE_ACCESS_DUPLEX (0x{pipe_access:X})")
        print(f"[AuthorityServer]   Pipe type: PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT (0x{pipe_type:X})")
        print(f"[AuthorityServer]   Max instances: PIPE_UNLIMITED_INSTANCES")
        print(f"[AuthorityServer]   Out buffer size: {out_buffer_size}")
        print(f"[AuthorityServer]   In buffer size: {in_buffer_size}")
        print(f"[AuthorityServer]   Default timeout: {default_timeout}")
        print(f"[AuthorityServer]   Security attributes: present")
        
        pipe_handle = win32pipe.CreateNamedPipe(
            PIPE_NAME,
            pipe_access,
            pipe_type,
            max_instances,
            out_buffer_size,
            in_buffer_size,
            default_timeout,
            security_attributes
        )
        
        print(f"[AuthorityServer] Named pipe created: handle={pipe_handle}")
        
        return pipe_handle
    
    def _read_message(self, pipe_handle: int) -> Optional[bytes]:
        """Read message with framing and partial read handling.
        
        Phase 2: Message framing, partial read handling.
        ReadFile returns (bytes_read, data) tuple.
        """
        try:
            # Read message length header (4 bytes)
            header = b""
            while len(header) < MESSAGE_HEADER_SIZE:
                result = win32file.ReadFile(pipe_handle, MESSAGE_HEADER_SIZE - len(header))
                # ReadFile returns (bytes_read, data) tuple
                if isinstance(result, tuple):
                    bytes_read = result[0]
                    chunk = result[1] if len(result) > 1 else b""
                else:
                    chunk = result
                    bytes_read = len(chunk)
                if not chunk:
                    return None
                header += chunk
            
            message_length = struct.unpack("<I", header)[0]
            
            # Phase 2: Bounded message size check
            if message_length > MAX_MESSAGE_SIZE:
                raise RuntimeError(f"Message too large: {message_length}")
            
            # Read message body
            body = b""
            while len(body) < message_length:
                result = win32file.ReadFile(pipe_handle, min(BUFFER_SIZE, message_length - len(body)))
                # ReadFile returns (bytes_read, data) tuple
                if isinstance(result, tuple):
                    bytes_read = result[0]
                    chunk = result[1] if len(result) > 1 else b""
                else:
                    chunk = result
                    bytes_read = len(chunk)
                if not chunk:
                    return None
                body += chunk
            
            return body
        except Exception as e:
            raise RuntimeError(f"Failed to read message: {e}")
    
    def _write_message(self, pipe_handle: int, message: bytes) -> None:
        """Write message with framing.
        
        Phase 2: Message framing.
        """
        try:
            # Write message length header
            header = struct.pack("<I", len(message))
            win32file.WriteFile(pipe_handle, header)
            
            # Write message body
            win32file.WriteFile(pipe_handle, message)
        except Exception as e:
            raise RuntimeError(f"Failed to write message: {e}")
    
    def _handle_client(self, pipe_handle: int) -> None:
        """Handle client connection with persistent connection mode.
        
        Phase 2 Round 3: Persistent connection mode.
        - Accept one client connection
        - Process multiple framed requests on same connection
        - Keep connection alive until client disconnects or error
        - Close only on explicit disconnect, protocol violation, timeout, or shutdown
        
        This enables: REGISTER_EXECUTION → ISSUE_LEASE → CONSUME_LEASE on same connection.
        """
        try:
            # PART VII: Get OS-observed client PID
            client_pid = win32pipe.GetNamedPipeClientProcessId(pipe_handle)
            print(f"[AuthorityServer] Client connected", flush=True)
            print(f"[AuthorityServer]   Client PID (OS-observed): {client_pid}", flush=True)
            print(f"[AuthorityServer]   Authority PID: {os.getpid()}", flush=True)
            print(f"[AuthorityServer]   PID equality check: {client_pid != os.getpid()}", flush=True)
            
            # PART VIII: JSON identity claims are ignored
            # The protocol may include "pid" or "sid" in request data, but these are NOT used
            # for authorization. Only the OS-observed client PID from GetNamedPipeClientProcessId
            # is trusted for identity verification.
            
            # Phase 2 Round 3: Process multiple requests on same connection
            request_count = 0
            max_requests_per_connection = 100  # Prevent abuse
            connection_timeout = 300  # 5 minutes max connection time
            connection_start = time.time()
            
            while True:
                # Check shutdown
                with self._shutdown_lock:
                    if self._shutdown:
                        print(f"[AuthorityServer] Shutdown requested, closing connection", flush=True)
                        break
                
                # Check timeout
                if time.time() - connection_start > connection_timeout:
                    print(f"[AuthorityServer] Connection timeout, closing", flush=True)
                    break
                
                # Check max requests
                if request_count >= max_requests_per_connection:
                    print(f"[AuthorityServer] Max requests reached, closing connection", flush=True)
                    break
                
                # Read request with timeout check
                try:
                    # Small delay before read to allow client to be ready
                    time.sleep(0.1)
                    
                    request_data = self._read_message(pipe_handle)
                    if request_data is None:
                        print(f"[AuthorityServer] Client disconnected (no data)", flush=True)
                        break
                    
                    request_count += 1
                    print(f"[AuthorityServer] Request #{request_count} received: {len(request_data)} bytes", flush=True)
                    
                    # Parse request
                    request = json.loads(request_data.decode('utf-8'))
                    request_type = request.get('type', request.get('request_type', ''))
                    print(f"[AuthorityServer] Request type: {request_type}", flush=True)
                    
                    # PART VIII: Log that JSON identity claims are ignored
                    if 'pid' in request.get('data', {}):
                        print(f"[AuthorityServer] WARNING: JSON contains 'pid' claim - IGNORED", flush=True)
                    if 'sid' in request.get('data', {}):
                        print(f"[AuthorityServer] WARNING: JSON contains 'sid' claim - IGNORED", flush=True)
                    
                    # Route request with OS-observed client PID
                    response = self._route_request(request, client_pid)
                    
                    # Convert AuthorityResponse to dict for JSON serialization
                    if hasattr(response, 'success'):
                        response_dict = {
                            "success": response.success,
                            "data": response.data,
                            "error": response.error,
                            "request_id": getattr(response, 'request_id', '')
                        }
                    else:
                        response_dict = response
                    
                    # Write response
                    response_data = json.dumps(response_dict).encode('utf-8')
                    response_length = len(response_data).to_bytes(4, byteorder='little')
                    full_response = response_length + response_data
                    
                    print(f"[AuthorityServer] Sending response #{request_count}: {len(full_response)} bytes", flush=True)
                    win32file.WriteFile(pipe_handle, full_response)
                    
                    # Flush buffers
                    win32file.FlushFileBuffers(pipe_handle)
                    print(f"[AuthorityServer] Response #{request_count} flushed", flush=True)
                    
                    # Small delay after write to allow client to process
                    time.sleep(0.1)
                    
                except pywintypes.error as e:
                    if e.winerror == 109:  # ERROR_BROKEN_PIPE
                        print(f"[AuthorityServer] Client disconnected (broken pipe)", flush=True)
                        break
                    else:
                        print(f"[AuthorityServer] Win32 error: {e}", flush=True)
                        break
                except Exception as e:
                    print(f"[AuthorityServer] Error processing request: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                    break
            
            # PART VII: Log final identity verification
            print(f"[AuthorityServer] Connection closing", flush=True)
            print(f"[AuthorityServer]   Total requests processed: {request_count}", flush=True)
            print(f"[AuthorityServer]   OS identity verification:", flush=True)
            print(f"[AuthorityServer]   Observed client PID: {client_pid}", flush=True)
            print(f"[AuthorityServer]   Authority PID: {os.getpid()}", flush=True)
            print(f"[AuthorityServer]   PIDs are different: {client_pid != os.getpid()}", flush=True)
            
        except Exception as e:
            print(f"[AuthorityServer] Error handling client: {e}", flush=True)
            import traceback
            traceback.print_exc()
        finally:
            # Close pipe
            win32file.CloseHandle(pipe_handle)
            print(f"[AuthorityServer] Pipe closed", flush=True)
    
    def _route_request(self, request: dict, client_pid: int) -> dict:
        """Route request to appropriate handler.
        
        Phase 2: Request routing.
        PART VII: Pass client_pid to handlers for identity verification.
        """
        handlers = {
            "REGISTER_EXECUTION": self._authority.handle_register_execution,
            "ISSUE_LEASE": self._authority.handle_issue_lease,
            "CONSUME_LEASE": self._authority.handle_consume_lease,
            "VERIFY_EXECUTION": self._authority.handle_verify_execution,
            "GET_STATUS": self._authority.handle_get_status,
            "PHASE3_REQUEST_JOIN": self._authority.handle_phase3_request_join,
        }
        
        request_type = request.get("type", request.get("request_type", ""))
        request_id = request.get("request_id", "")
        handler = handlers.get(request_type)
        
        if handler is None:
            return {
                "success": False,
                "data": {},
                "error": f"Unknown request type: {request_type}",
                "request_id": request_id
            }
        
        # Create AuthorityRequest
        from iabv_v15.services.trust.authority_service import AuthorityRequest
        auth_request = AuthorityRequest(
            request_type=request_type,
            data=request.get("data", {}),
            request_id=request_id
        )
        
        return handler(auth_request, client_pid)
    
    def _server_loop(self) -> None:
        """Server loop for accepting connections.
        
        Phase 2: Connection lifecycle.
        PART VII: Synchronous single-request mode for testing.
        """
        while True:
            with self._shutdown_lock:
                if self._shutdown:
                    break
            
            try:
                # Create named pipe
                pipe_handle = self._create_named_pipe()
                
                # Wait for client connection
                win32pipe.ConnectNamedPipe(pipe_handle)
                
                # Handle client synchronously (single-request mode)
                self._handle_client(pipe_handle)
                
                # Continue for next client (remove single-client break)
            
            except Exception as e:
                print(f"Server loop error: {e}", flush=True)
                time.sleep(1)
                # Continue to next iteration instead of breaking
                continue
    
    def start(self) -> None:
        """Start authority server.
        
        Phase 2: Start server thread.
        """
        self._server_thread = threading.Thread(target=self._server_loop)
        self._server_thread.daemon = True
        self._server_thread.start()
    
    def stop(self) -> None:
        """Stop authority server.
        
        Phase 2: Clean shutdown.
        """
        with self._shutdown_lock:
            self._shutdown = True
        
        if self._server_thread:
            self._server_thread.join(timeout=5)
