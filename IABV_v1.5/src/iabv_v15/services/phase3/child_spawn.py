"""Parent Child Spawn Logic for Phase 3.

This module implements the parent-side child process spawn logic for Phase 3.

Key properties:
- Create child with restrictive security descriptor (SYSTEM owner)
- Create anonymous pipe for credential delivery
- Bind read handle to child stdin
- Write private_key to pipe
- Close parent read-side after spawn
- Close write handle after delivery
- Retain hProcess for lifecycle operations
"""

from __future__ import annotations

import ctypes
import os
import sys
import win32process
import win32security
import win32con
import win32api
from typing import Tuple, Optional

# Windows API constants for PROC_THREAD_ATTRIBUTE_HANDLE_LIST
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x20002  # 131074

# Load kernel32 for attribute list functions
kernel32 = ctypes.windll.kernel32

from iabv_v15.services.phase3.process_security import create_restrictive_child_security_descriptor
from iabv_v15.services.phase3.credential_transport import AnonymousPipeCredentialTransport
from iabv_v15.services.phase3.ed25519_keys import Ed25519KeyPair


class ChildSpawnError(Exception):
    """Child spawn error."""
    pass


class ChildSpawnResult:
    """Result of child process spawn."""
    
    def __init__(
        self,
        hProcess: int,
        hThread: int,
        child_pid: int,
        child_tid: int
    ):
        """Initialize child spawn result.
        
        Args:
            hProcess: Handle to child process
            hThread: Handle to child thread
            child_pid: Child process ID
            child_tid: Child thread ID
        """
        self.hProcess = hProcess
        self.hThread = hThread
        self.child_pid = child_pid
        self.child_tid = child_tid
    
    def close_thread_handle(self) -> None:
        """Close thread handle (not needed for lifecycle)."""
        if self.hThread is not None:
            win32api.CloseHandle(self.hThread)
            self.hThread = None
    
    def close_process_handle(self) -> None:
        """Close process handle when done."""
        if self.hProcess is not None:
            win32api.CloseHandle(self.hProcess)
            self.hProcess = None


def spawn_child_with_credential(
    command_line: str,
    private_key: Ed25519KeyPair,
    join_token: str,
    subject_id: str,
    execution_id: str,
    working_directory: Optional[str] = None
) -> ChildSpawnResult:
    """Spawn child process with credential delivery.
    
    This implements the approved Round 15 design with HANDLE_LIST:
    - Create child with restrictive security descriptor (SYSTEM owner)
    - Create anonymous pipe for credential delivery
    - Bind read handle to child stdin
    - Use STARTUPINFOEX with PROC_THREAD_ATTRIBUTE_HANDLE_LIST
    - Only stdin read handle is inheritable
    - Write private_key to pipe
    - Close parent read-side after spawn
    - Close write handle after delivery
    - Retain hProcess for lifecycle operations
    
    Args:
        command_line: Command line for child process
        private_key: Ed25519 key pair (private key will be delivered)
        join_token: Join token for child
        subject_id: Subject ID
        execution_id: Execution ID
        working_directory: Working directory for child (optional)
        
    Returns:
        ChildSpawnResult containing process handles and IDs
        
    Raises:
        ChildSpawnError: If child spawn fails
    """
    transport = None
    attribute_list = None
    
    try:
        # Step 1: Create anonymous pipe for credential delivery
        transport = AnonymousPipeCredentialTransport()
        read_handle, write_handle = transport.create_pipe()
        
        # Step 2: Create restrictive security descriptor
        security_descriptor = create_restrictive_child_security_descriptor()
        
        # Convert security descriptor to binary
        sd_binary = security_descriptor.GetSecurityDescriptorBinary()
        
        # Step 3: Create SECURITY_ATTRIBUTES
        security_attributes = win32security.SECURITY_ATTRIBUTES()
        security_attributes.SECURITY_DESCRIPTOR = sd_binary
        security_attributes.bInheritHandle = True
        
        # Step 4: Create STARTUPINFOEX with explicit handle list
        si = win32process.STARTUPINFOEX()
        si.StartupInfo.cb = ctypes.sizeof(si)
        
        # Step 5: Initialize attribute list for 1 attribute
        # Using ctypes to call InitializeProcThreadAttributeList
        kernel32.InitializeProcThreadAttributeList.restype = ctypes.c_size_t
        kernel32.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(ctypes.c_size_t)]
        
        # First call to get required size
        size = ctypes.c_size_t()
        kernel32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
        
        # Allocate buffer
        attribute_list = ctypes.create_string_buffer(size.value)
        
        # Second call to initialize
        if not kernel32.InitializeProcThreadAttributeList(attribute_list, 1, 0, ctypes.byref(size)):
            raise ChildSpawnError("Failed to initialize attribute list")
        
        si.lpAttributeList = attribute_list
        
        # Step 6: Set handle list attribute (only stdin read handle)
        handle_list = [read_handle]
        handle_array = (ctypes.c_void_p * len(handle_list))()
        for i, handle in enumerate(handle_list):
            handle_array[i] = handle
        
        # Using ctypes to call UpdateProcThreadAttribute
        kernel32.UpdateProcThreadAttribute.restype = ctypes.c_bool
        kernel32.UpdateProcThreadAttribute.argtypes = [
            ctypes.c_void_p,  # attribute list
            ctypes.c_ulong,   # flags
            ctypes.c_ulong,   # attribute (PROC_THREAD_ATTRIBUTE_HANDLE_LIST)
            ctypes.c_void_p,  # value (handle array)
            ctypes.c_size_t,  # size
            ctypes.c_void_p,  # previous value (optional)
            ctypes.POINTER(ctypes.c_size_t)  # return size (optional)
        ]
        
        if not kernel32.UpdateProcThreadAttribute(
            attribute_list,
            0,
            PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
            handle_array,
            ctypes.sizeof(ctypes.c_void_p) * len(handle_list),
            None,
            None
        ):
            raise ChildSpawnError("Failed to update attribute list")
        
        # Step 7: Set stdin bound to pipe
        si.StartupInfo.dwFlags = win32process.STARTF_USESTDHANDLES
        si.StartupInfo.hStdInput = read_handle
        si.StartupInfo.hStdOutput = win32api.GetStdHandle(win32api.STD_OUTPUT_HANDLE)
        si.StartupInfo.hStdError = win32api.GetStdHandle(win32api.STD_ERROR_HANDLE)
        
        # Step 8: Build command line with arguments
        full_command = f"{command_line} --join_token {join_token} --subject_id {subject_id} --execution_id {execution_id}"
        
        # Step 9: Create process with security descriptor and explicit handle list
        result = win32process.CreateProcess(
            None,  # Application name (use command line)
            full_command,  # Command line
            security_attributes,  # Process security attributes
            None,  # Thread security attributes
            True,  # Inherit handles (restricted by attribute list)
            win32process.CREATE_NEW_PROCESS_GROUP,  # Creation flags
            None,  # Environment (inherit from parent)
            working_directory,  # Current directory
            si  # Startup info (STARTUPINFOEX with attribute list)
        )
        
        # result[0] is hProcess (parent's handle to child)
        # result[1] is hThread (parent's handle to child's primary thread)
        # result[2] is child_pid
        # result[3] is child_tid
        
        hProcess = result[0]
        hThread = result[1]
        child_pid = result[2]
        child_tid = result[3]
        
        # Step 10: Delete attribute list
        kernel32.DeleteProcThreadAttributeList.restype = None
        kernel32.DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
        kernel32.DeleteProcThreadAttributeList(attribute_list)
        attribute_list = None
        
        # Step 11: Close parent's read-side duplicate immediately after spawn
        transport.close_parent_read_handle()
        
        # Step 12: Write private_key to pipe
        # Use base64 encoding for safe transport
        private_key_base64 = private_key.get_private_key_base64()
        transport.write_credential(private_key_base64.encode('utf-8'))
        
        # Step 13: Close write handle to signal EOF
        transport.close_write_handle()
        
        # Step 14: Create result object
        spawn_result = ChildSpawnResult(
            hProcess=hProcess,
            hThread=hThread,
            child_pid=child_pid,
            child_tid=child_tid
        )
        
        # Step 15: Close thread handle (not needed for lifecycle)
        spawn_result.close_thread_handle()
        
        return spawn_result
        
    except Exception as e:
        # Cleanup on error
        if attribute_list is not None:
            try:
                win32procthread.DeleteProcThreadAttributeList(attribute_list)
            except Exception:
                pass
        if transport is not None:
            transport.cleanup()
        
        raise ChildSpawnError(f"Child spawn failed: {e}")
