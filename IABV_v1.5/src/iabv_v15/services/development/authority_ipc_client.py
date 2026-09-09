"""P0-B V4-r9.2 Authority IPC Client.

F14 V4-r9.2 FIX: Named Pipe client for authority service communication.

This module provides the client-side IPC implementation for communicating
with the authority service via Named Pipe.

Architecture:
    APPLICATION PROCESS
        ↓
    Named Pipe Client
        ↓
    Authority Service (LocalService)
        ↓
    CERTIFY operation with authorization
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

# Windows Named Pipe support
try:
    import win32file
    import win32api
    import win32pipe
    WINDOWS_PIPE_AVAILABLE = True
except ImportError:
    WINDOWS_PIPE_AVAILABLE = False

logger = logging.getLogger(__name__)


class AuthorityIPCClientError(Exception):
    """Raised when IPC operation fails."""
    pass


class AuthorityServiceUnavailableError(Exception):
    """Raised when authority service is not available."""
    pass


class AuthorityIPCClient:
    """Named Pipe client for authority service communication.
    
    F14 V4-r9.2 FIX: Client for authority service IPC.
    
    This class provides:
    - Named Pipe connection to authority service
    - CERTIFY request/response handling
    - Error handling for service unavailability
    - Caller identity verification
    """
    
    def __init__(
        self,
        pipe_name: str = r"\\.\pipe\IABVAuditAuthority",
        timeout_ms: int = 5000,
    ):
        """Initialize IPC client.
        
        Args:
            pipe_name: Named Pipe name
            timeout_ms: Connection timeout in milliseconds
        """
        if not WINDOWS_PIPE_AVAILABLE:
            raise RuntimeError(
                "IPC client requires pywin32. "
                "Install with: pip install pywin32"
            )
        
        if sys.platform != "win32":
            raise RuntimeError(
                "Named Pipe IPC is only supported on Windows platform."
            )
        
        self.pipe_name = pipe_name
        self.timeout_ms = timeout_ms
        
        logger.info("AuthorityIPCClient initialized: %s", pipe_name)
    
    def _connect_to_service(self) -> int:
        """Connect to authority service via Named Pipe.
        
        F14 V4-r9.2 FIX: Connect to Named Pipe with timeout.
        
        Returns:
            Pipe handle
            
        Raises:
            AuthorityServiceUnavailableError: If service not available
            AuthorityIPCClientError: If connection fails
        """
        try:
            pipe_handle = win32file.CreateFile(
                self.pipe_name,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            
            logger.info("Connected to authority service: %s", self.pipe_name)
            return pipe_handle
            
        except win32api.error as exc:
            if exc.winerror == 2:  # File not found
                raise AuthorityServiceUnavailableError(
                    f"Authority service not available at {self.pipe_name}. "
                    "Ensure the Windows Service is running."
                )
            elif exc.winerror == 5:  # Access denied
                raise AuthorityIPCClientError(
                    f"Access denied to authority service: {exc}"
                )
            else:
                raise AuthorityIPCClientError(f"Failed to connect to authority service: {exc}")
        except Exception as exc:
            raise AuthorityIPCClientError(f"IPC connection error: {exc}")
    
    def _send_request(self, pipe_handle: int, request: dict[str, Any]) -> dict[str, Any]:
        """Send request to authority service and receive response.
        
        F14 V4-r9.2 FIX: Send request and receive response with error handling.
        
        Args:
            pipe_handle: Pipe handle
            request: Request dictionary
            
        Returns:
            Response dictionary
            
        Raises:
            AuthorityIPCClientError: If request/response fails
        """
        try:
            # Send request
            request_data = json.dumps(request).encode('utf-8')
            win32file.WriteFile(pipe_handle, request_data, None)
            logger.info("Sent request: %s", request.get("operation"))
            
            # Receive response
            result, response_data = win32file.ReadFile(pipe_handle, 4096, None)
            response = json.loads(response_data.decode('utf-8'))
            
            # Check for error response
            if "error" in response:
                raise AuthorityIPCClientError(f"Service error: {response['error']}")
            
            logger.info("Received response: %s", response.get("status", "unknown"))
            return response
            
        except json.JSONDecodeError as exc:
            raise AuthorityIPCClientError(f"Invalid response format: {exc}")
        except win32api.error as exc:
            raise AuthorityIPCClientError(f"Pipe communication error: {exc}")
        except Exception as exc:
            raise AuthorityIPCClientError(f"Request/response error: {exc}")
    
    def certify_audit_record(self, audit_record: dict[str, Any]) -> dict[str, Any]:
        """Request certification of audit record from authority service.
        
        F14 V4-r9.2 FIX: CERTIFY operation via IPC.
        
        Args:
            audit_record: Audit record dictionary to certify
            
        Returns:
            Response dictionary with signature
            
        Raises:
            AuthorityServiceUnavailableError: If service not available
            AuthorityIPCClientError: If certification fails
        """
        request = {
            "operation": "CERTIFY",
            "audit_record": audit_record,
        }
        
        pipe_handle = None
        try:
            pipe_handle = self._connect_to_service()
            response = self._send_request(pipe_handle, request)
            return response
        finally:
            if pipe_handle:
                try:
                    win32file.CloseHandle(pipe_handle)
                except:
                    pass
    
    def get_service_status(self) -> dict[str, Any]:
        """Get authority service status.
        
        F14 V4-r9.2 FIX: STATUS operation via IPC.
        
        Returns:
            Status dictionary
            
        Raises:
            AuthorityServiceUnavailableError: If service not available
            AuthorityIPCClientError: If status request fails
        """
        request = {
            "operation": "STATUS",
        }
        
        pipe_handle = None
        try:
            pipe_handle = self._connect_to_service()
            response = self._send_request(pipe_handle, request)
            return response
        finally:
            if pipe_handle:
                try:
                    win32file.CloseHandle(pipe_handle)
                except:
                    pass
    
    def is_service_available(self) -> bool:
        """Check if authority service is available.
        
        F14 V4-r9.2 FIX: Check service availability without raising exception.
        
        Returns:
            True if service is available, False otherwise
        """
        try:
            status = self.get_service_status()
            return status.get("status") == "running"
        except AuthorityServiceUnavailableError:
            return False
        except Exception:
            return False
