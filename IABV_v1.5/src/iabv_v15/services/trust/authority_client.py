"""Authority Client: Windows Named Pipe client for P0.213 V5 Phase 2.

This client communicates with the separate authority process via Windows Named Pipe.

CRITICAL: This client runs in the worker process and communicates with the authority
process via IPC. The worker cannot access the authority's secret key directly.

Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)
"""

from __future__ import annotations

import json
import os
import struct
import time
from typing import Any, Optional

import pywintypes
import win32file
import win32pipe

from iabv_v15.services.trust.authority_service import (
    AuthorityRequest,
    AuthorityResponse
)
from iabv_v15.services.trust.authority_protocol import (
    RegisterExecutionRequest,
    RegisterExecutionResponse,
    IssueLeaseRequest,
    IssueLeaseResponse,
    ConsumeLeaseRequest,
    ConsumeLeaseResponse,
)


# Message framing constants
MESSAGE_HEADER_SIZE = 4  # 4-byte little-endian length header
BUFFER_SIZE = 4096
MAX_MESSAGE_SIZE = 1 * 1024 * 1024  # 1MB max message size
PIPE_NAME = r"\\.\pipe\IABV_Authority"
MAX_CONNECTION_ATTEMPTS = 30
CONNECTION_RETRY_DELAY = 0.5


class AuthorityClient:
    """Client for communicating with the authority process via Windows Named Pipe.
    
    Phase 2 Round 3: Persistent connection mode.
    
    CANONICAL IPC LIFECYCLE:
    - connect(): Establishes one persistent connection to authority process
    - register_execution(): Sends REGISTER_EXECUTION request on same connection
    - issue_lease(): Sends ISSUE_LEASE request on same connection
    - consume_lease(): Sends CONSUME_LEASE request on same connection
    - disconnect(): Closes the connection
    
    The server processes multiple requests on the same connection until:
    - Client explicitly calls disconnect()
    - Connection timeout (5 minutes)
    - Max requests reached (100)
    - Protocol violation or error
    - Authority shutdown
    
    This enables: REGISTER_EXECUTION → ISSUE_LEASE → CONSUME_LEASE on same connection.
    """
    
    def __init__(self, pipe_name: str = PIPE_NAME) -> None:
        """Initialize authority client.
        
        Args:
            pipe_name: Named pipe name (default: IABV_Authority)
        """
        self._pipe_name = pipe_name
        self._pipe_handle: Optional[int] = None
    
    def connect(self) -> None:
        """Connect to authority process via Named Pipe.
        
        Phase 2: Real IPC connection with retry logic.
        PART II: Instrumented to log exact access parameters.
        PART IV: Log client token SID for SID match verification.
        """
        if self._pipe_handle is not None:
            raise RuntimeError("Already connected")
        
        # PART IV: Get client token SID
        import win32security
        import win32api
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32security.TOKEN_QUERY)
        user_sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        
        # PART III: Capture client process identity from actual Windows token
        print(f"[AuthorityClient] Client process identity:", flush=True)
        print(f"[AuthorityClient]   PID: {os.getpid()}", flush=True)
        print(f"[AuthorityClient]   Username: {os.environ.get('USERNAME', 'unknown')}", flush=True)
        print(f"[AuthorityClient]   Token User SID: {user_sid}", flush=True)
        
        # Get session ID
        try:
            session_id = win32security.GetTokenInformation(token, win32security.TokenSessionId)
            print(f"[AuthorityClient]   Session ID: {session_id}", flush=True)
        except:
            print(f"[AuthorityClient]   Session ID: (unavailable)", flush=True)
        
        # Get integrity level
        try:
            integrity = win32security.GetTokenInformation(token, win32security.TokenIntegrityLevel)
            print(f"[AuthorityClient]   Integrity Level: {integrity}", flush=True)
        except:
            print(f"[AuthorityClient]   Integrity Level: (unavailable)", flush=True)
        
        # Check for thread token
        try:
            thread_token = win32security.OpenThreadToken(win32api.GetCurrentThread(), win32security.TOKEN_QUERY, True)
            thread_sid = win32security.GetTokenInformation(thread_token, win32security.TokenUser)[0]
            print(f"[AuthorityClient]   Thread Token SID: {thread_sid}", flush=True)
            print(f"[AuthorityClient]   Thread token differs from process token: {thread_sid != user_sid}", flush=True)
        except:
            print(f"[AuthorityClient]   Thread Token: (none)", flush=True)
        
        print(f"[AuthorityClient] Connecting to {self._pipe_name}...", flush=True)
        print(f"[AuthorityClient] Desired access: GENERIC_READ | GENERIC_WRITE", flush=True)
        print(f"[AuthorityClient] Share mode: 0 (no sharing)", flush=True)
        print(f"[AuthorityClient] Creation disposition: OPEN_EXISTING", flush=True)
        print(f"[AuthorityClient] Flags/attributes: 0", flush=True)
        
        for attempt in range(MAX_CONNECTION_ATTEMPTS):
            try:
                desired_access = win32file.GENERIC_READ | win32file.GENERIC_WRITE
                share_mode = 0
                creation_disposition = win32file.OPEN_EXISTING
                flags_and_attributes = 0
                
                print(f"[AuthorityClient] Attempt {attempt + 1}: CreateFile", flush=True)
                print(f"[AuthorityClient]   desired_access=0x{desired_access:X}", flush=True)
                print(f"[AuthorityClient]   share_mode=0x{share_mode:X}", flush=True)
                print(f"[AuthorityClient]   creation_disposition=0x{creation_disposition:X}", flush=True)
                print(f"[AuthorityClient]   flags_and_attributes=0x{flags_and_attributes:X}", flush=True)
                
                self._pipe_handle = win32file.CreateFile(
                    self._pipe_name,
                    desired_access,
                    share_mode,
                    None,
                    creation_disposition,
                    flags_and_attributes,
                    None
                )
                print(f"[AuthorityClient] Connected on attempt {attempt + 1}", flush=True)
                print(f"[AuthorityClient] Pipe handle: {self._pipe_handle}", flush=True)
                return
            except pywintypes.error as e:
                print(f"[AuthorityClient] Win32 error on attempt {attempt + 1}:", flush=True)
                print(f"[AuthorityClient]   Error code: {e.winerror}", flush=True)
                print(f"[AuthorityClient]   Error message: {e.strerror}", flush=True)
                print(f"[AuthorityClient]   Function: {e.funcname}", flush=True)
                
                if e.winerror == 2:  # ERROR_FILE_NOT_FOUND
                    print(f"[AuthorityClient] Pipe not found (attempt {attempt + 1}/{MAX_CONNECTION_ATTEMPTS})", flush=True)
                elif e.winerror == 5:  # ERROR_ACCESS_DENIED
                    print(f"[AuthorityClient] ACCESS DENIED (attempt {attempt + 1}/{MAX_CONNECTION_ATTEMPTS})", flush=True)
                elif e.winerror == 231:  # ERROR_PIPE_BUSY
                    print(f"[AuthorityClient] Pipe busy (attempt {attempt + 1}/{MAX_CONNECTION_ATTEMPTS})", flush=True)
                else:
                    print(f"[AuthorityClient] Connection error: {e} (attempt {attempt + 1}/{MAX_CONNECTION_ATTEMPTS})", flush=True)
                
                if attempt < MAX_CONNECTION_ATTEMPTS - 1:
                    time.sleep(CONNECTION_RETRY_DELAY)
        
        raise RuntimeError(f"Failed to connect to authority pipe after {MAX_CONNECTION_ATTEMPTS} attempts")
    
    def disconnect(self) -> None:
        """Disconnect from authority process.
        
        Phase 2: Clean pipe closure.
        """
        if self._pipe_handle is not None:
            try:
                win32file.CloseHandle(self._pipe_handle)
            except:
                pass
            self._pipe_handle = None
            print(f"[AuthorityClient] Disconnected")
    
    def _normalize_readfile_result(self, result) -> tuple[int, bytes]:
        """Normalize win32file.ReadFile result to (bytes_read, data).
        
        pywin32 ReadFile returns (bytes_read, data) tuple.
        This helper normalizes the result to a consistent format.
        """
        if isinstance(result, tuple):
            if len(result) >= 2:
                # Assume (bytes_read, data) format
                bytes_read = result[0]
                data = result[1] if len(result) > 1 else b""
            elif len(result) == 1:
                # Single element tuple, assume it's data
                data = result[0]
                bytes_read = len(data) if isinstance(data, bytes) else 0
            else:
                # Empty tuple
                bytes_read = 0
                data = b""
        else:
            # Not a tuple, assume it's data
            data = result
            bytes_read = len(data) if isinstance(data, bytes) else 0
        
        return bytes_read, data
    
    def _send_request(self, request: AuthorityRequest) -> AuthorityResponse:
        """Send request to authority process.
        
        Phase 2: Real IPC communication with framing.
        """
        if self._pipe_handle is None:
            raise RuntimeError("Not connected to authority")
        
        # Serialize request
        request_data = {
            "type": request.request_type,
            "data": request.data,
            "request_id": request.request_id
        }
        request_json = json.dumps(request_data).encode('utf-8')
        
        # Add framing
        message_length = len(request_json).to_bytes(4, byteorder='little')
        full_message = message_length + request_json
        
        print(f"[AuthorityClient] Sending request: {request.request_type}, {len(full_message)} bytes", flush=True)
        
        # Write message
        win32file.WriteFile(self._pipe_handle, full_message)
        
        print(f"[AuthorityClient] Request sent, waiting for response...", flush=True)
        
        # Read response
        response = self._read_response()
        
        print(f"[AuthorityClient] Response received", flush=True)
        
        return response
    
    def _read_response(self) -> AuthorityResponse:
        """Read response from authority process.
        
        Phase 2: Real IPC communication with framing.
        Uses _normalize_readfile_result to handle pywin32 ReadFile return format.
        """
        if self._pipe_handle is None:
            raise RuntimeError("Not connected to authority")
        
        # Read message length header
        header = b""
        while len(header) < MESSAGE_HEADER_SIZE:
            result = win32file.ReadFile(self._pipe_handle, MESSAGE_HEADER_SIZE - len(header))
            bytes_read, chunk = self._normalize_readfile_result(result)
            if not chunk:
                raise RuntimeError("Failed to read response header")
            header += chunk
        
        message_length = struct.unpack("<I", header)[0]
        
        # Phase 2: Bounded message size check
        if message_length > MAX_MESSAGE_SIZE:
            raise RuntimeError(f"Response too large: {message_length}")
        
        # Read message body
        body = b""
        while len(body) < message_length:
            result = win32file.ReadFile(self._pipe_handle, min(BUFFER_SIZE, message_length - len(body)))
            bytes_read, chunk = self._normalize_readfile_result(result)
            if not chunk:
                raise RuntimeError("Failed to read response body")
            body += chunk
        
        # Parse response
        try:
            response_data = json.loads(body.decode('utf-8'))
            return AuthorityResponse(
                success=response_data.get("success", False),
                data=response_data.get("data", {}),
                error=response_data.get("error", None)
            )
        except Exception as e:
            raise RuntimeError(f"Failed to parse response: {e}")
    
    def get_status(self) -> dict:
        """Get authority status.
        
        Phase 2: Real IPC call to authority process.
        """
        import uuid
        request_id = str(uuid.uuid4())
        request = AuthorityRequest(
            request_type="GET_STATUS",
            data={},
            request_id=request_id
        )
        response = self._send_request(request)
        
        if not response.success:
            raise RuntimeError(f"Failed to get status: {response.error}")
        
        return response.data
    
    def register_execution(
        self,
        invocation_id: str,
        action: str,
        target: str,
        requested_scope: str,
        task_context: Optional[str] = None,
        episode_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Register execution with authority using canonical protocol.
        
        Args:
            invocation_id: Unique invocation identifier
            action: Requested operation (e.g., "READ", "WRITE")
            target: Requested target (e.g., "codebase", "repo")
            requested_scope: Caller's requested authorization scope
            task_context: Task/development objective context (e.g., "self_analysis")
            episode_id: Optional episode identifier
            session_id: Optional session identifier
        
        Returns:
            Registration result dictionary with authority-derived fields
        """
        request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data=RegisterExecutionRequest(
                invocation_id=invocation_id,
                action=action,
                target=target,
                requested_scope=requested_scope,
                task_context=task_context,
                episode_id=episode_id,
                session_id=session_id
            ).to_dict(),
            request_id=invocation_id
        )
        response = self._send_request(request)
        
        if not response.success:
            raise RuntimeError(f"Failed to register execution: {response.error}")
        
        return response.data
    
    def issue_lease(
        self,
        run_id: str,
        execution_id: str,
        requested_ttl_seconds: Optional[int] = None
    ) -> dict[str, Any]:
        """Issue lease using canonical protocol.
        
        Args:
            run_id: Authority-owned run identifier (from registration)
            execution_id: Authority-owned execution identifier (from registration)
            requested_ttl_seconds: Requested lease TTL in seconds (optional)
        
        Returns:
            Lease data dictionary with authority-derived fields
        """
        request = AuthorityRequest(
            request_type="ISSUE_LEASE",
            data=IssueLeaseRequest(
                run_id=run_id,
                execution_id=execution_id,
                requested_ttl_seconds=requested_ttl_seconds
            ).to_dict(),
            request_id=run_id
        )
        response = self._send_request(request)
        
        if not response.success:
            raise RuntimeError(f"Failed to issue lease: {response.error}")
        
        return response.data
    
    def consume_lease(
        self,
        lease_id: str,
        execution_id: str
    ) -> dict[str, Any]:
        """Consume lease using canonical protocol.
        
        Args:
            lease_id: Authority-owned lease identifier
            execution_id: Authority-owned execution identifier (from registration)
        
        Returns:
            Consumption result dictionary
        """
        request = AuthorityRequest(
            request_type="CONSUME_LEASE",
            data=ConsumeLeaseRequest(
                lease_id=lease_id,
                execution_id=execution_id
            ).to_dict(),
            request_id=lease_id
        )
        response = self._send_request(request)
        
        if not response.success:
            raise RuntimeError(f"Failed to consume lease: {response.error}")
        
        return response.data
    
    def verify_execution(
        self,
        invocation_id: str,
        expected_scope: str
    ) -> dict[str, Any]:
        """Verify execution identity.
        
        Args:
            invocation_id: Invocation identifier
            expected_scope: Expected authorized scope
        
        Returns:
            Verification result dictionary
        """
        request = AuthorityRequest(
            request_type="VERIFY_EXECUTION",
            data={
                "invocation_id": invocation_id,
                "expected_scope": expected_scope
            },
            request_id=invocation_id
        )
        response = self._send_request(request)
        
        if not response.success:
            raise RuntimeError(f"Failed to verify execution: {response.error}")
        
        return response.data


# Import dataclasses after AuthorityRequest/AuthorityResponse are defined
import dataclasses
