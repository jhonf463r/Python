"""Minimal controlled diagnostic test for IABV Named Pipe

This script performs a step-by-step diagnostic to determine the exact
failure point of the IABV Named Pipe implementation.

NO CODE CHANGES - ONLY DIAGNOSTIC CAPTURE.
"""

import os
import sys
import time
import subprocess
import win32file
import win32pipe
import win32api
import win32security
import pywintypes
from pathlib import Path

# Configuration
PIPE_NAME = r"\\.\pipe\IABV_Authority"
TIMEOUT_AUTHORITY_START = 15
TIMEOUT_PIPE_CREATION = 15
TIMEOUT_CLIENT_CONNECT = 10

def get_process_info(pid=None):
    """Capture process identity information."""
    if pid:
        try:
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
            # Get process info from handle
            # This is simplified - in practice we'd need more complex calls
            return {'pid': pid, 'status': 'alive'}
        except:
            return {'pid': pid, 'status': 'dead'}
    else:
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

def check_pipe_exists(pipe_name):
    """Check if named pipe exists."""
    try:
        # Try to open pipe with minimal access to check existence
        handle = win32file.CreateFile(
            pipe_name,
            win32file.GENERIC_READ,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        win32file.CloseHandle(handle)
        return True
    except pywintypes.error as e:
        if e.winerror == 2:  # ERROR_FILE_NOT_FOUND
            return False
        elif e.winerror == 231:  # ERROR_PIPE_BUSY
            return True  # Pipe exists but busy
        else:
            return False

def main():
    print("=" * 80)
    print("MINIMAL CONTROLLED DIAGNOSTIC TEST - IABV Named Pipe")
    print("=" * 80)
    
    diagnostic = {}
    
    # STEP 1: START AUTHORITY
    print("\n[STEP 1] Starting Authority process...")
    print(f"[STEP 1] Timeout: {TIMEOUT_AUTHORITY_START}s")
    
    authority_script = Path(__file__).parent.parent.parent / "src" / "iabv_v15" / "services" / "trust" / "authority_process.py"
    
    try:
        process = subprocess.Popen(
            [sys.executable, str(authority_script), "--pipe-name", PIPE_NAME, "--storage-root", "temp_authority_storage"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        authority_pid = process.pid
        diagnostic['AUTHORITY_PID'] = authority_pid
        print(f"[STEP 1] Authority PID: {authority_pid}")
        
        # Wait for process to start
        time.sleep(2)
        
        # Check if process is still alive
        if process.poll() is None:
            diagnostic['AUTHORITY_STATUS'] = 'alive'
            print(f"[STEP 1] Authority process is alive")
        else:
            diagnostic['AUTHORITY_STATUS'] = 'dead'
            diagnostic['AUTHORITY_EXIT_CODE'] = process.returncode
            print(f"[STEP 1] Authority process died immediately with exit code: {process.returncode}")
            stdout, stderr = process.communicate()
            print(f"[STEP 1] STDOUT: {stdout}")
            print(f"[STEP 1] STDERR: {stderr}")
            return diagnostic
            
    except Exception as e:
        diagnostic['AUTHORITY_STATUS'] = 'start_failed'
        diagnostic['AUTHORITY_ERROR'] = str(e)
        print(f"[STEP 1] Failed to start authority: {e}")
        return diagnostic
    
    # STEP 2: CAPTURE PROCESS INFO
    print("\n[STEP 2] Capturing process information...")
    server_info = get_process_info()
    diagnostic['USERNAME'] = server_info['username']
    diagnostic['SESSION_ID'] = server_info['session_id']
    print(f"[STEP 2] Username: {server_info['username']}")
    print(f"[STEP 2] Session ID: {server_info['session_id']}")
    
    # STEP 3: WAIT FOR PIPE CREATION
    print("\n[STEP 3] Waiting for pipe creation...")
    print(f"[STEP 3] Timeout: {TIMEOUT_PIPE_CREATION}s")
    
    pipe_created = False
    for i in range(TIMEOUT_PIPE_CREATION):
        if check_pipe_exists(PIPE_NAME):
            pipe_created = True
            print(f"[STEP 3] Pipe created after {i} seconds")
            break
        time.sleep(1)
    
    diagnostic['PIPE_EXISTS'] = pipe_created
    diagnostic['PIPE_NAME_SERVER'] = PIPE_NAME
    
    if not pipe_created:
        print(f"[STEP 3] Pipe NOT created after {TIMEOUT_PIPE_CREATION}s")
        # Terminate authority
        process.terminate()
        time.sleep(1)
        if process.poll() is None:
            process.kill()
        return diagnostic
    
    print(f"[STEP 3] Pipe exists: {PIPE_NAME}")
    
    # STEP 4: ATTEMPT CLIENT CONNECTION
    print("\n[STEP 4] Attempting client connection...")
    print(f"[STEP 4] Timeout: {TIMEOUT_CLIENT_CONNECT}s")
    
    client_info = get_process_info()
    diagnostic['CLIENT_PID'] = client_info['pid']
    diagnostic['PIPE_NAME_CLIENT'] = PIPE_NAME
    
    print(f"[STEP 4] Client PID: {client_info['pid']}")
    print(f"[STEP 4] Pipe name: {PIPE_NAME}")
    print(f"[STEP 4] Pipe name length: {len(PIPE_NAME)}")
    print(f"[STEP 4] Pipe name repr: {repr(PIPE_NAME)}")
    
    connect_start = time.time()
    try:
        pipe_handle = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        connect_time = time.time() - connect_start
        diagnostic['CONNECT_RESULT'] = 'success'
        diagnostic['CONNECT_TIME'] = connect_time
        print(f"[STEP 4] Connected successfully in {connect_time:.2f}s")
        win32file.CloseHandle(pipe_handle)
    except pywintypes.error as e:
        connect_time = time.time() - connect_start
        diagnostic['CONNECT_RESULT'] = 'failed'
        diagnostic['CONNECT_TIME'] = connect_time
        diagnostic['WIN32_ERROR_CODE'] = e.winerror
        diagnostic['WIN32_ERROR_TEXT'] = e.strerror
        diagnostic['WIN32_FUNCTION'] = e.funcname
        print(f"[STEP 4] Connection failed after {connect_time:.2f}s")
        print(f"[STEP 4] Error code: {e.winerror}")
        print(f"[STEP 4] Error message: {e.strerror}")
        print(f"[STEP 4] Function: {e.funcname}")
    
    # STEP 5: CHECK SERVER STATE
    print("\n[STEP 5] Checking server state...")
    if process.poll() is None:
        diagnostic['SERVER_ALIVE'] = True
        print(f"[STEP 5] Server is still alive")
    else:
        diagnostic['SERVER_ALIVE'] = False
        diagnostic['AUTHORITY_EXIT_CODE'] = process.returncode
        print(f"[STEP 5] Server died with exit code: {process.returncode}")
    
    # STEP 6: TERMINATE AUTHORITY
    print("\n[STEP 6] Terminating Authority process...")
    process.terminate()
    time.sleep(2)
    if process.poll() is None:
        process.kill()
        time.sleep(1)
    print(f"[STEP 6] Authority terminated")
    
    # FINAL REPORT
    print("\n" + "=" * 80)
    print("DIAGNOSTIC RESULTS")
    print("=" * 80)
    for key, value in diagnostic.items():
        print(f"{key}: {value}")
    
    return diagnostic

if __name__ == "__main__":
    import win32con
    result = main()
    sys.exit(0)
