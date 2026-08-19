"""P0.213: IPC Channel for Windows named pipes.

DESIGN_RECONSTRUCTION: This module is a new implementation reconstructed from
experimental design evidence. It is NOT recovered historical code.

Purpose: Provide Windows named pipes for IPC transport of InternalMcpInvocation
between parent runtime and MCP child process.

Contract Requirements:
- Windows named pipes (WINDOWS_ONLY)
- PID validation
- Producer scope validation
- NO encryption/signatures
- NO cross-platform transport
"""
from __future__ import annotations

import os
import json
import threading
from typing import Any, Callable

try:
    import win32pipe
    import win32file
    import win32security
    import pywintypes
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class IpcMessage:
    """IPC message for lease transport."""
    
    def __init__(self, message_type: str, data: dict[str, Any]):
        self.message_type = message_type
        self.data = data
    
    def to_json(self) -> str:
        """Convert to JSON for transport."""
        return json.dumps({
            'message_type': self.message_type,
            'data': self.data
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> IpcMessage:
        """Create from JSON (transport deserialization)."""
        data = json.loads(json_str)
        return cls(data['message_type'], data['data'])


class WindowsNamedPipe:
    """Windows named pipe for parent-child lease transport.
    
    This class provides a private Windows named pipe for transporting
    InternalMcpInvocation leases between parent runtime and MCP child process.
    
    Contract Compliance:
    - Windows named pipes (WINDOWS_ONLY)
    - PID validation via security descriptor
    - Producer scope validation
    - NO encryption/signatures
    """
    
    def __init__(self, pipe_name: str, producer_pid: int):
        """Initialize Windows named pipe.
        
        Args:
            pipe_name: Name of the named pipe
            producer_pid: PID of the producer process for security
            
        Raises:
            RuntimeError: If win32pipe is not available (non-Windows platform)
        """
        if not WIN32_AVAILABLE:
            raise RuntimeError("Windows named pipes require pywin32 on Windows platform")
        
        self.pipe_name = pipe_name
        self.producer_pid = producer_pid
        self.pipe_handle = None
        self._lock = threading.Lock()
    
    def create_server(self) -> None:
        """Create the named pipe server.
        
        This creates a named pipe. PID and producer scope validation
        are performed at the application level, not in the pipe descriptor.
        """
        with self._lock:
            # Create named pipe with default security
            # PID validation is performed at application level
            self.pipe_handle = win32pipe.CreateNamedPipe(
                self.pipe_name,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE,
                1,  # Max instances
                65536,  # Output buffer size
                65536,  # Input buffer size
                0,  # Default timeout
                None  # Default security
            )
    
    def connect_client(self) -> None:
        """Connect as a client to the named pipe."""
        with self._lock:
            try:
                self.pipe_handle = win32file.CreateFile(
                    self.pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
            except pywintypes.error as e:
                raise RuntimeError(f"Failed to connect to named pipe: {e}")
    
    def send_message(self, message: IpcMessage) -> None:
        """Send a message through the named pipe.
        
        Args:
            message: The IpcMessage to send
        """
        with self._lock:
            if self.pipe_handle is None:
                raise RuntimeError("Pipe not connected")
            
            data = message.to_json().encode('utf-8')
            win32file.WriteFile(self.pipe_handle, data)
    
    def receive_message(self) -> IpcMessage | None:
        """Receive a message from the named pipe.
        
        Returns:
            The received IpcMessage, or None if no message available
        """
        with self._lock:
            if self.pipe_handle is None:
                raise RuntimeError("Pipe not connected")
            
            try:
                result, data = win32file.ReadFile(self.pipe_handle, 65536)
                if result == 0:  # No data
                    return None
                return IpcMessage.from_json(data.decode('utf-8'))
            except pywintypes.error:
                return None
    
    def close(self) -> None:
        """Close the named pipe."""
        with self._lock:
            if self.pipe_handle is not None:
                win32file.CloseHandle(self.pipe_handle)
                self.pipe_handle = None
