"""Minimal Windows Named Pipe Server - Control Experiment

This is a minimal control experiment to test basic Named Pipe IPC
without any IABV code. Purpose: Determine if GitHub-hosted Windows
CI can perform simple cross-process Named Pipe connections.

DO NOT use this for production IABV transport.
"""

import sys
import time
import os
import win32pipe
import win32file
import win32api
import win32security
import pywintypes

PIPE_NAME = r"\\.\pipe\ControlPipeTest"
BUFFER_SIZE = 4096

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
    print("CONTROL PIPE SERVER - Minimal Named Pipe Test")
    print("=" * 80)
    
    # Record process info
    server_info = get_process_info()
    print(f"\n[SERVER] Process Information:")
    print(f"[SERVER]   PID: {server_info['pid']}")
    print(f"[SERVER]   Username: {server_info['username']}")
    print(f"[SERVER]   User SID: {server_info['user_sid']}")
    print(f"[SERVER]   Session ID: {server_info['session_id']}")
    
    print(f"\n[SERVER] Creating Named Pipe: {PIPE_NAME}")
    
    try:
        # Create named pipe with simplest possible configuration
        pipe_handle = win32pipe.CreateNamedPipe(
            PIPE_NAME,
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            win32pipe.PIPE_UNLIMITED_INSTANCES,
            BUFFER_SIZE,
            BUFFER_SIZE,
            0,
            None  # No security attributes for maximum compatibility
        )
        
        print(f"[SERVER] Pipe created successfully")
        print(f"[SERVER] Pipe handle: {pipe_handle}")
        
        # Create ready signal
        ready_file = "control_pipe_ready.txt"
        with open(ready_file, 'w') as f:
            f.write(f"READY\nPID={server_info['pid']}\nPIPE={PIPE_NAME}\n")
        print(f"[SERVER] Ready signal created: {ready_file}")
        
        print(f"[SERVER] Waiting for client connection...")
        print(f"[SERVER] Calling ConnectNamedPipe (blocking)...")
        
        # Wait for client
        win32pipe.ConnectNamedPipe(pipe_handle)
        print(f"[SERVER] Client connected!")
        
        # Get client info
        try:
            client_pid = win32pipe.GetNamedPipeClientProcessId(pipe_handle)
            print(f"[SERVER] Client PID: {client_pid}")
        except Exception as e:
            print(f"[SERVER] Error getting client PID: {e}")
        
        # Read message from client
        print(f"[SERVER] Reading message from client...")
        result = win32file.ReadFile(pipe_handle, BUFFER_SIZE)
        if isinstance(result, tuple):
            bytes_read, data = result
        else:
            data = result
            bytes_read = len(data)
        
        message = data.decode('utf-8')
        print(f"[SERVER] Received message ({bytes_read} bytes): {message}")
        
        # Send response
        response = f"ACK: {message}".encode('utf-8')
        win32file.WriteFile(pipe_handle, response)
        print(f"[SERVER] Sent response: {response.decode('utf-8')}")
        
        # Cleanup
        time.sleep(1)
        win32file.CloseHandle(pipe_handle)
        print(f"[SERVER] Pipe closed")
        
        print(f"\n[SERVER] CONTROL TEST PASSED")
        return 0
        
    except Exception as e:
        print(f"\n[SERVER] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
