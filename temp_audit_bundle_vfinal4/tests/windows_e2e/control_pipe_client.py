"""Minimal Windows Named Pipe Client - Control Experiment

This is a minimal control experiment to test basic Named Pipe IPC
without any IABV code. Purpose: Determine if GitHub-hosted Windows
CI can perform simple cross-process Named Pipe connections.

DO NOT use this for production IABV transport.
"""

import sys
import time
import os
import win32file
import win32api
import win32security
import pywintypes

PIPE_NAME = r"\\.\pipe\ControlPipeTest"
BUFFER_SIZE = 4096
MAX_ATTEMPTS = 30
RETRY_DELAY = 0.5

def get_process_info():
    """Capture process identity information."""
    pid = os.getpid()
    username = os.environ.get('USERNAME', 'unknown')
    
    try:
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32security.TOKEN_QUERY)
        user_sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]
        session_id = win32security.GetTokenInformation(token, win32security.TokenSessionId)
    except Exception as e:
        user_sid = f"Error: {e}"
        session_id = "Error"
    
    return {
        'pid': pid,
        'username': username,
        'user_sid': str(user_sid),
        'session_id': session_id
    }

def main():
    print("=" * 80)
    print("CONTROL PIPE CLIENT - Minimal Named Pipe Test")
    print("=" * 80)
    
    # Record process info
    client_info = get_process_info()
    print(f"\n[CLIENT] Process Information:")
    print(f"[CLIENT]   PID: {client_info['pid']}")
    print(f"[CLIENT]   Username: {client_info['username']}")
    print(f"[CLIENT]   User SID: {client_info['user_sid']}")
    print(f"[CLIENT]   Session ID: {client_info['session_id']}")
    
    print(f"\n[CLIENT] Attempting to connect to: {PIPE_NAME}")
    print(f"[CLIENT] Pipe name length: {len(PIPE_NAME)}")
    print(f"[CLIENT] Pipe name repr: {repr(PIPE_NAME)}")
    
    # Wait for ready signal
    print(f"\n[CLIENT] Waiting for server ready signal...")
    ready_file = "control_pipe_ready.txt"
    for attempt in range(30):
        if os.path.exists(ready_file):
            print(f"[CLIENT] Ready signal found")
            with open(ready_file, 'r') as f:
                content = f.read()
                print(f"[CLIENT] Ready signal content:\n{content}")
            break
        time.sleep(0.5)
    else:
        print(f"[CLIENT] ERROR: Ready signal not found after 15 seconds")
        return 1
    
    # Additional delay to ensure pipe is ready
    time.sleep(2)
    
    # Attempt connection
    for attempt in range(MAX_ATTEMPTS):
        try:
            print(f"\n[CLIENT] Attempt {attempt + 1}/{MAX_ATTEMPTS}: CreateFile")
            
            pipe_handle = win32file.CreateFile(
                PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0,  # No sharing
                None,
                win32file.OPEN_EXISTING,
                0,
                None
            )
            
            print(f"[CLIENT] Connected successfully on attempt {attempt + 1}")
            print(f"[CLIENT] Pipe handle: {pipe_handle}")
            
            # Send message
            message = "Hello from control client".encode('utf-8')
            print(f"[CLIENT] Sending message: {message.decode('utf-8')}")
            win32file.WriteFile(pipe_handle, message)
            
            # Read response
            print(f"[CLIENT] Reading response...")
            result = win32file.ReadFile(pipe_handle, BUFFER_SIZE)
            if isinstance(result, tuple):
                bytes_read, data = result
            else:
                data = result
                bytes_read = len(data)
            
            response = data.decode('utf-8')
            print(f"[CLIENT] Received response ({bytes_read} bytes): {response}")
            
            # Cleanup
            win32file.CloseHandle(pipe_handle)
            print(f"[CLIENT] Pipe closed")
            
            print(f"\n[CLIENT] CONTROL TEST PASSED")
            return 0
            
        except pywintypes.error as e:
            print(f"[CLIENT] Win32 error on attempt {attempt + 1}:")
            print(f"[CLIENT]   Error code: {e.winerror}")
            print(f"[CLIENT]   Error message: {e.strerror}")
            print(f"[CLIENT]   Function: {e.funcname}")
            
            if e.winerror == 2:  # ERROR_FILE_NOT_FOUND
                print(f"[CLIENT]   Pipe not found")
            elif e.winerror == 5:  # ERROR_ACCESS_DENIED
                print(f"[CLIENT]   ACCESS DENIED")
            elif e.winerror == 231:  # ERROR_PIPE_BUSY
                print(f"[CLIENT]   Pipe busy")
            
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY)
    
    print(f"\n[CLIENT] ERROR: Failed to connect after {MAX_ATTEMPTS} attempts")
    return 1

if __name__ == "__main__":
    sys.exit(main())
