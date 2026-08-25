"""Anonymous Pipe Credential Transport for Phase 3.

This module implements the approved Round 9 design for delivering private keys
via anonymous pipes with inherited handles.

Key properties:
- Anonymous pipe (no name)
- Child-side read handle inheritable
- Parent-side write handle non-inheritable
- Child reads from stdin
- Parent closes read-side after spawn
- Parent closes write handle after delivery
"""

from __future__ import annotations

import os
import sys
import win32pipe
import win32file
import win32api
import win32con
import pywintypes
from typing import Tuple


class AnonymousPipeCredentialTransport:
    """Anonymous pipe for private key delivery."""
    
    def __init__(self):
        """Initialize anonymous pipe credential transport."""
        self.read_handle: int | None = None
        self.write_handle: int | None = None
        self.parent_read_handle: int | None = None
    
    def create_pipe(self) -> Tuple[int, int]:
        """Create anonymous pipe for credential delivery.
        
        Returns:
            (read_handle, write_handle) tuple
            - read_handle: Child-side read handle (inheritable)
            - write_handle: Parent-side write handle (non-inheritable)
        """
        # Create anonymous pipe
        self.read_handle, self.write_handle = win32pipe.CreatePipe(
            None,  # Default security attributes
            0,     # Default buffer size
            0      # Default timeout
        )
        
        # Make read handle inheritable for child
        win32api.SetHandleInformation(
            self.read_handle,
            win32con.HANDLE_FLAG_INHERIT,
            win32con.HANDLE_FLAG_INHERIT
        )
        
        # Keep a duplicate for parent (non-inheritable)
        self.parent_read_handle = win32api.DuplicateHandle(
            win32api.GetCurrentProcess(),
            self.read_handle,
            win32api.GetCurrentProcess(),
            0,
            False,  # Not inheritable
            win32con.DUPLICATE_SAME_ACCESS
        )
        
        # Close original read handle (parent doesn't need inheritable copy)
        win32api.CloseHandle(self.read_handle)
        self.read_handle = self.parent_read_handle
        
        return self.read_handle, self.write_handle
    
    def write_credential(self, credential: bytes) -> None:
        """Write credential to pipe.
        
        Args:
            credential: Credential bytes to write
        """
        if self.write_handle is None:
            raise RuntimeError("Pipe not created")
        
        # Write credential to pipe
        win32file.WriteFile(self.write_handle, credential)
        
        # Flush to ensure delivery
        win32file.FlushFileBuffers(self.write_handle)
    
    def close_parent_read_handle(self) -> None:
        """Close parent's read-side duplicate after process creation."""
        if self.parent_read_handle is not None:
            win32api.CloseHandle(self.parent_read_handle)
            self.parent_read_handle = None
    
    def close_write_handle(self) -> None:
        """Close write handle to signal EOF."""
        if self.write_handle is not None:
            win32api.CloseHandle(self.write_handle)
            self.write_handle = None
    
    def cleanup(self) -> None:
        """Clean up all handles."""
        if self.parent_read_handle is not None:
            win32api.CloseHandle(self.parent_read_handle)
            self.parent_read_handle = None
        
        if self.write_handle is not None:
            win32api.CloseHandle(self.write_handle)
            self.write_handle = None


def read_credential_from_stdin() -> bytes:
    """Read credential from stdin (child process).
    
    This is the FIRST meaningful operation in the child process.
    Reads until EOF, then closes stdin.
    
    Returns:
        Credential bytes
    """
    # Read all data from stdin until EOF
    credential = sys.stdin.read()
    
    # Validate credential format
    if not credential:
        raise ValueError("Empty credential received")
    
    # Close stdin immediately after reading
    sys.stdin.close()
    
    return credential.encode('utf-8')
