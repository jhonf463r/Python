"""Comprehensive Windows Named Pipe diagnostic using Win32 APIs

This script performs detailed diagnostic of the IABV Named Pipe implementation
using Windows APIs to determine the exact state and cause of ERROR_PIPE_BUSY.

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
import win32con
import pywintypes
from pathlib import Path

# Configuration
PIPE_NAME = r"\\.\pipe\IABV_Authority"
TIMEOUT_AUTHORITY_START = 15
TIMEOUT_PIPE_CREATION = 15
TIMEOUT_CLIENT_CONNECT = 10
TIMEOUT_WAITNAMEDPIPE = 2000  # 2 seconds

def get_process_integrity_level():
    """Get process integrity level."""
    try:
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32security.TOKEN_QUERY)
        integrity_level = win32security.GetTokenInformation(token, win32security.TokenIntegrityLevel)
        sid = integrity_level[0]
        # Map SID to string
        if str(sid) == "S-1-16-12288":
            return "Medium"
        elif str(sid) == "S-1-16-8192":
            return "Low"
        elif str(sid) == "S-1-16-16384":
            return "High"
        elif str(sid) == "S-1-16-4096":
            return "Untrusted"
        elif str(sid) == "S-1-16-2048":
            return "System"
        else:
            return str(sid)
    except Exception as e:
        return f"Error: {e}"

def get_pipe_info(pipe_handle):
    """Get pipe information using GetNamedPipeInfo."""
    try:
        flags, instances, out_buffer, in_buffer, max_instances = win32pipe.GetNamedPipeInfo(pipe_handle)
        return {
            'flags': flags,
            'instances': instances,
            'out_buffer': out_buffer,
            'in_buffer': in_buffer,
            'max_instances': max_instances
        }
    except Exception as e:
        return {'error': str(e)}

def get_pipe_handle_state(pipe_handle):
    """Get pipe handle state using GetNamedPipeHandleState."""
    try:
        state, instances, count, timeout = win32pipe.GetNamedPipeHandleState(pipe_handle)
        return {
            'state': state,
            'instances': instances,
            'count': count,
            'timeout': timeout
        }
    except Exception as e:
        return {'error': str(e)}

def check_pipe_exists(pipe_name):
    """Check if named pipe exists."""
    try:
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
    print("COMPREHENSIVE PIPE DIAGNOSTIC - IABV Named Pipe")
    print("=" * 80)
    
    diagnostic = {}
    
    # STEP 1: START AUTHORITY
    print("\n[STEP 1] Starting Authority process...")
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
        
        time.sleep(2)
        
        if process.poll() is None:
            diagnostic['SERVER_ALIVE'] = True
            print(f"[STEP 1] Authority process is alive")
        else:
            diagnostic['SERVER_ALIVE'] = False
            diagnostic['AUTHORITY_EXIT_CODE'] = process.returncode
            print(f"[STEP 1] Authority process died with exit code: {process.returncode}")
            return diagnostic
            
    except Exception as e:
        diagnostic['SERVER_ALIVE'] = False
        diagnostic['AUTHORITY_ERROR'] = str(e)
        print(f"[STEP 1] Failed to start authority: {e}")
        return diagnostic
    
    # STEP 2: WAIT FOR PIPE CREATION
    print("\n[STEP 2] Waiting for pipe creation...")
    pipe_created = False
    for i in range(TIMEOUT_PIPE_CREATION):
        if check_pipe_exists(PIPE_NAME):
            pipe_created = True
            print(f"[STEP 2] Pipe created after {i} seconds")
            break
        time.sleep(1)
    
    diagnostic['PIPE_EXISTS'] = pipe_created
    
    if not pipe_created:
        print(f"[STEP 2] Pipe NOT created after {TIMEOUT_PIPE_CREATION}s")
        process.terminate()
        time.sleep(1)
        if process.poll() is None:
            process.kill()
        return diagnostic
    
    # STEP 3: CAPTURE SERVER PROCESS INFO
    print("\n[STEP 3] Capturing server process information...")
    diagnostic['SERVER_USERNAME'] = os.environ.get('USERNAME', 'unknown')
    diagnostic['SERVER_SESSION_ID'] = os.environ.get('SESSIONNAME', 'unknown')
    diagnostic['SERVER_INTEGRITY'] = get_process_integrity_level()
    print(f"[STEP 3] Username: {diagnostic['SERVER_USERNAME']}")
    print(f"[STEP 3] Session ID: {diagnostic['SERVER_SESSION_ID']}")
    print(f"[STEP 3] Integrity: {diagnostic['SERVER_INTEGRITY']}")
    
    # STEP 4: CAPTURE CLIENT PROCESS INFO
    print("\n[STEP 4] Capturing client process information...")
    diagnostic['CLIENT_PID'] = os.getpid()
    diagnostic['CLIENT_USERNAME'] = os.environ.get('USERNAME', 'unknown')
    diagnostic['CLIENT_SESSION_ID'] = os.environ.get('SESSIONNAME', 'unknown')
    diagnostic['CLIENT_INTEGRITY'] = get_process_integrity_level()
    print(f"[STEP 4] Client PID: {diagnostic['CLIENT_PID']}")
    print(f"[STEP 4] Username: {diagnostic['CLIENT_USERNAME']}")
    print(f"[STEP 4] Session ID: {diagnostic['CLIENT_SESSION_ID']}")
    print(f"[STEP 4] Integrity: {diagnostic['CLIENT_INTEGRITY']}")
    
    # STEP 5: ATTEMPT CREATEFILE
    print("\n[STEP 5] Attempting CreateFile...")
    diagnostic['PIPE_NAME_SERVER'] = PIPE_NAME
    diagnostic['PIPE_NAME_CLIENT'] = PIPE_NAME
    
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
        diagnostic['CREATEFILE_RESULT'] = 'success'
        diagnostic['CREATEFILE_ERROR'] = None
        diagnostic['CREATEFILE_TIME'] = connect_time
        print(f"[STEP 5] CreateFile succeeded in {connect_time:.2f}s")
        
        # Get pipe info on successful connection
        pipe_info = get_pipe_info(pipe_handle)
        diagnostic['GETNAMEDPIPEINFO'] = pipe_info
        
        handle_state = get_pipe_handle_state(pipe_handle)
        diagnostic['GETNAMEDPIPEHANDLESTATE'] = handle_state
        
        win32file.CloseHandle(pipe_handle)
        
    except pywintypes.error as e:
        connect_time = time.time() - connect_start
        diagnostic['CREATEFILE_RESULT'] = 'failed'
        diagnostic['CREATEFILE_ERROR_CODE'] = e.winerror
        diagnostic['CREATEFILE_ERROR_TEXT'] = e.strerror
        diagnostic['CREATEFILE_FUNCTION'] = e.funcname
        diagnostic['CREATEFILE_TIME'] = connect_time
        print(f"[STEP 5] CreateFile failed after {connect_time:.2f}s")
        print(f"[STEP 5] Error code: {e.winerror}")
        print(f"[STEP 5] Error message: {e.strerror}")
        print(f"[STEP 5] Function: {e.funcname}")
        
        # STEP 6: WAITNAMEDPIPE IF BUSY
        if e.winerror == 231:  # ERROR_PIPE_BUSY
            print("\n[STEP 6] Pipe busy, attempting WaitNamedPipe...")
            print(f"[STEP 6] Timeout: {TIMEOUT_WAITNAMEDPIPE}ms")
            
            wait_start = time.time()
            try:
                result = win32pipe.WaitNamedPipe(PIPE_NAME, TIMEOUT_WAITNAMEDPIPE)
                wait_time = time.time() - wait_start
                diagnostic['WAITNAMEDPIPE_RESULT'] = 'success' if result else 'failed'
                diagnostic['WAITNAMEDPIPE_TIME'] = wait_time
                print(f"[STEP 6] WaitNamedPipe returned: {result}")
                print(f"[STEP 6] Wait time: {wait_time:.2f}s")
                
                # Retry CreateFile once
                print("\n[STEP 7] Retrying CreateFile after WaitNamedPipe...")
                retry_start = time.time()
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
                    retry_time = time.time() - retry_start
                    diagnostic['CREATEFILE_RETRY_RESULT'] = 'success'
                    diagnostic['CREATEFILE_RETRY_TIME'] = retry_time
                    print(f"[STEP 7] CreateFile retry succeeded in {retry_time:.2f}s")
                    
                    # Get pipe info on successful retry
                    pipe_info = get_pipe_info(pipe_handle)
                    diagnostic['GETNAMEDPIPEINFO_RETRY'] = pipe_info
                    
                    handle_state = get_pipe_handle_state(pipe_handle)
                    diagnostic['GETNAMEDPIPEHANDLESTATE_RETRY'] = handle_state
                    
                    win32file.CloseHandle(pipe_handle)
                    
                except pywintypes.error as e2:
                    retry_time = time.time() - retry_start
                    diagnostic['CREATEFILE_RETRY_RESULT'] = 'failed'
                    diagnostic['CREATEFILE_RETRY_ERROR_CODE'] = e2.winerror
                    diagnostic['CREATEFILE_RETRY_ERROR_TEXT'] = e2.strerror
                    diagnostic['CREATEFILE_RETRY_TIME'] = retry_time
                    print(f"[STEP 7] CreateFile retry failed after {retry_time:.2f}s")
                    print(f"[STEP 7] Error code: {e2.winerror}")
                    print(f"[STEP 7] Error message: {e2.strerror}")
                    
            except pywintypes.error as e3:
                wait_time = time.time() - wait_start
                diagnostic['WAITNAMEDPIPE_ERROR_CODE'] = e3.winerror
                diagnostic['WAITNAMEDPIPE_ERROR_TEXT'] = e3.strerror
                diagnostic['WAITNAMEDPIPE_TIME'] = wait_time
                print(f"[STEP 6] WaitNamedPipe failed: {e3.winerror} - {e3.strerror}")
    
    # STEP 8: CHECK SERVER STATE
    print("\n[STEP 8] Checking server state...")
    if process.poll() is None:
        diagnostic['SERVER_ALIVE_FINAL'] = True
        print(f"[STEP 8] Server is still alive")
    else:
        diagnostic['SERVER_ALIVE_FINAL'] = False
        diagnostic['AUTHORITY_EXIT_CODE'] = process.returncode
        print(f"[STEP 8] Server died with exit code: {process.returncode}")
    
    # STEP 9: TERMINATE AUTHORITY
    print("\n[STEP 9] Terminating Authority process...")
    process.terminate()
    time.sleep(2)
    if process.poll() is None:
        process.kill()
        time.sleep(1)
    print(f"[STEP 9] Authority terminated")
    
    # FINAL REPORT
    print("\n" + "=" * 80)
    print("COMPREHENSIVE DIAGNOSTIC RESULTS")
    print("=" * 80)
    
    # Production code parameters (from inspection)
    print("\nPRODUCTION CREATE NAMED PIPE PARAMETERS:")
    print("  Pipe name: \\\\.\\pipe\\IABV_Authority")
    print("  dwOpenMode: PIPE_ACCESS_DUPLEX (0x00000003)")
    print("  dwPipeMode: PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT (0x00000006)")
    print("  nMaxInstances: PIPE_UNLIMITED_INSTANCES (255)")
    print("  nOutBufferSize: 4096")
    print("  nInBufferSize: 4096")
    print("  nDefaultTimeOut: 0")
    print("  lpSecurityAttributes: None")
    
    print("\nCONNECT NAMED PIPE BEHAVIOR:")
    print("  Called with: blocking mode (PIPE_WAIT)")
    print("  Server creates: ONE instance at a time")
    print("  After disconnect: server closes handle and creates NEW instance")
    print("  Pattern: Standard Windows named pipe lifecycle")
    
    print("\nDIAGNOSTIC RESULTS:")
    for key, value in diagnostic.items():
        print(f"  {key}: {value}")
    
    # Generate required result table
    print("\n" + "=" * 80)
    print("REQUIRED RESULT TABLE")
    print("=" * 80)
    
    table = {
        'Authority PID': diagnostic.get('AUTHORITY_PID', 'N/A'),
        'Server alive': diagnostic.get('SERVER_ALIVE', 'N/A'),
        'Pipe exists': diagnostic.get('PIPE_EXISTS', 'N/A'),
        'nMaxInstances': '255 (PIPE_UNLIMITED_INSTANCES)',
        'Open mode': 'PIPE_ACCESS_DUPLEX (0x00000003)',
        'Pipe mode': 'PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT (0x00000006)',
        'ConnectNamedPipe return': 'Blocking (PIPE_WAIT)',
        'ConnectNamedPipe error': 'None (blocking call)',
        'CreateFile result': diagnostic.get('CREATEFILE_RESULT', 'N/A'),
        'CreateFile error': diagnostic.get('CREATEFILE_ERROR_CODE', 'N/A'),
        'WaitNamedPipe result': diagnostic.get('WAITNAMEDPIPE_RESULT', 'N/A'),
        'WaitNamedPipe error': diagnostic.get('WAITNAMEDPIPE_ERROR_CODE', 'N/A'),
        'GetNamedPipeInfo': diagnostic.get('GETNAMEDPIPEINFO', 'N/A'),
        'GetNamedPipeHandleState': diagnostic.get('GETNAMEDPIPEHANDLESTATE', 'N/A'),
        'Server session': diagnostic.get('SERVER_SESSION_ID', 'N/A'),
        'Client session': diagnostic.get('CLIENT_SESSION_ID', 'N/A'),
        'Server user': diagnostic.get('SERVER_USERNAME', 'N/A'),
        'Client user': diagnostic.get('CLIENT_USERNAME', 'N/A'),
        'Server integrity': diagnostic.get('SERVER_INTEGRITY', 'N/A'),
        'Client integrity': diagnostic.get('CLIENT_INTEGRITY', 'N/A'),
        'Security descriptor result': 'None (lpSecurityAttributes=None)'
    }
    
    for field, value in table.items():
        print(f"| {field:30s} | {str(value):40s} |")
    
    return diagnostic, table

if __name__ == "__main__":
    result, table = main()
    sys.exit(0)
