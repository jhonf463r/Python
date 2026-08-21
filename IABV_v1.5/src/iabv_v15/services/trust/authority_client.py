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


# Message framing constants
MESSAGE_HEADER_SIZE = 4  # 4-byte little-endian length header
BUFFER_SIZE = 4096
MAX_MESSAGE_SIZE = 1 * 1024 * 1024  # 1MB max message size
PIPE_NAME = r"\\.\pipe\IABV_Authority"
MAX_CONNECTION_ATTEMPTS = 30
CONNECTION_RETRY_DELAY = 0.5


class AuthorityClient:
    """Client for communicating with the authority process via Windows Named Pipe.
    
    Phase 2: Real IPC communication with separate authority process.
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
        """
        if self._pipe_handle is not None:
            raise RuntimeError("Already connected")
        
        print(f"[AuthorityClient] Connecting to {self._pipe_name}...")
        print(f"[AuthorityClient] Desired access: GENERIC_READ | GENERIC_WRITE")
        print(f"[AuthorityClient] Share mode: 0 (no sharing)")
        print(f"[AuthorityClient] Creation disposition: OPEN_EXISTING")
        print(f"[AuthorityClient] Flags/attributes: 0")
        
        for attempt in range(MAX_CONNECTION_ATTEMPTS):
            try:
                desired_access = win32file.GENERIC_READ | win32file.GENERIC_WRITE
                share_mode = 0
                creation_disposition = win32file.OPEN_EXISTING
                flags_and_attributes = 0
                
                print(f"[AuthorityClient] Attempt {attempt + 1}: CreateFile")
                print(f"[AuthorityClient]   desired_access=0x{desired_access:X}")
                print(f"[AuthorityClient]   share_mode=0x{share_mode:X}")
                print(f"[AuthorityClient]   creation_disposition=0x{creation_disposition:X}")
                print(f"[AuthorityClient]   flags_and_attributes=0x{flags_and_attributes:X}")
                
                self._pipe_handle = win32file.CreateFile(
                    self._pipe_name,
                    desired_access,
                    share_mode,
                    None,
                    creation_disposition,
                    flags_and_attributes,
                    None
                )
                print(f"[AuthorityClient] Connected on attempt {attempt + 1}")
                print(f"[AuthorityClient] Pipe handle: {self._pipe_handle}")
                return
            except pywintypes.error as e:
                print(f"[AuthorityClient] Win32 error on attempt {attempt + 1}:")
                print(f"[AuthorityClient]   Error code: {e.winerror}")
                print(f"[AuthorityClient]   Error message: {e.strerror}")
                print(f"[AuthorityClient]   Function: {e.funcname}")
                
                if e.winerror == 2:  # ERROR_FILE_NOT_FOUND
                    print(f"[AuthorityClient] Pipe not found (attempt {attempt + 1}/{MAX_CONNECTION_ATTEMPTS})")
                elif e.winerror == 5:  # ERROR_ACCESS_DENIED
                    print(f"[AuthorityClient] ACCESS DENIED (attempt {attempt + 1}/{MAX_CONNECTION_ATTEMPTS})")
                elif e.winerror == 231:  # ERROR_PIPE_BUSY
                    print(f"[AuthorityClient] Pipe busy (attempt {attempt + 1}/{MAX_CONNECTION_ATTEMPTS})")
                else:
                    print(f"[AuthorityClient] Connection error: {e} (attempt {attempt + 1}/{MAX_CONNECTION_ATTEMPTS})")
                
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
        """Send request to authority process and read response.
        
        Phase 2: Real IPC communication with framing.
        """
        if self._pipe_handle is None:
            raise RuntimeError("Not connected to authority")
        
        # Serialize request
        request_data = dataclasses.asdict(request)
        request_json = json.dumps(request_data).encode('utf-8')
        
        print(f"[AuthorityClient] Sending request: {request.request_type}, {len(request_json)} bytes")
        
        # Write message with framing
        header = struct.pack("<I", len(request_json))
        win32file.WriteFile(self._pipe_handle, header)
        win32file.WriteFile(self._pipe_handle, request_json)
        
        print(f"[AuthorityClient] Request sent, waiting for response...")
        
        # Read response immediately (no delay)
        response = self._read_response()
        
        print(f"[AuthorityClient] Response received")
        
        # DO NOT disconnect here - let the caller manage connection lifecycle
        # This allows for multiple requests per connection if needed
        
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
    
    def get_status(self) -> dict[str, Any]:
        """Get authority status.
        
        Returns:
            Authority status dictionary
        """
        request = AuthorityRequest(
            request_type="GET_STATUS",
            data={},
            request_id=""
        )
        response = self._send_request(request)
        
        if not response.success:
            raise RuntimeError(f"Failed to get status: {response.error}")
        
        return response.data
    
    def register_execution(
        self,
        invocation_id: str,
        authorized_scope: str,
        episode_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Register execution with authority.
        
        Args:
            invocation_id: Unique invocation identifier
            authorized_scope: Authorized scope for this execution
            episode_id: Optional episode identifier
            session_id: Optional session identifier
        
        Returns:
            Registration result dictionary
        """
        request = AuthorityRequest(
            request_type="REGISTER_EXECUTION",
            data={
                "invocation_id": invocation_id,
                "authorized_scope": authorized_scope,
                "episode_id": episode_id,
                "session_id": session_id
            },
            request_id=invocation_id
        )
        response = self._send_request(request)
        
        if not response.success:
            raise RuntimeError(f"Failed to register execution: {response.error}")
        
        return response.data
    
    def issue_lease(
        self,
        invocation_id: str,
        scope: str,
        duration_ms: int
    ) -> dict[str, Any]:
        """Issue lease for execution.
        
        Args:
            invocation_id: Unique invocation identifier
            scope: Lease scope
            duration_ms: Lease duration in milliseconds
        
        Returns:
            Lease data dictionary
        """
        request = AuthorityRequest(
            request_type="ISSUE_LEASE",
            data={
                "invocation_id": invocation_id,
                "scope": scope,
                "duration_ms": duration_ms
            },
            request_id=invocation_id
        )
        response = self._send_request(request)
        
        if not response.success:
            raise RuntimeError(f"Failed to issue lease: {response.error}")
        
        return response.data
    
    def consume_lease(
        self,
        lease_id: str,
        invocation_id: str
    ) -> dict[str, Any]:
        """Consume lease.
        
        Args:
            lease_id: Lease identifier
            invocation_id: Invocation identifier
        
        Returns:
            Consumption result dictionary
        """
        request = AuthorityRequest(
            request_type="CONSUME_LEASE",
            data={
                "lease_id": lease_id,
                "invocation_id": invocation_id
            },
            request_id=invocation_id
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
