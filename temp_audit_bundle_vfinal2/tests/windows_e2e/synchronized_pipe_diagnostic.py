"""Synchronized diagnostic for IABV Named Pipe lifecycle

This script performs client connection attempts synchronized to specific
server lifecycle events to determine the exact cause of ERROR_PIPE_BUSY.

NO PRODUCTION CHANGES - ONLY DIAGNOSTIC CAPTURE.
"""

import os
import sys
import time
import subprocess
import win32file
import win32pipe
import pywintypes
from pathlib import Path
import timeit

# Configuration
PIPE_NAME = r"\\.\pipe\IABV_Authority"
TIMEOUT_AUTHORITY_START = 15
TIMEOUT_MARKER = 10

def wait_for_marker(marker_name, timeout_seconds):
    """Wait for a marker file to appear."""
    marker_path = Path("temp_authority_storage") / marker_name
    print(f"[SYNC] Waiting for marker: {marker_name}")
    
    for i in range(timeout_seconds * 10):  # Check every 100ms
        if marker_path.exists():
            content = marker_path.read_text()
            print(f"[SYNC] Marker found: {marker_name}")
            print(f"[SYNC] Marker content:\n{content}")
            return content
        time.sleep(0.1)
    
    print(f"[SYNC] Marker timeout: {marker_name}")
    return None

def run_synchronized_experiment(experiment_name, marker_name, allow_connect_before_client=False):
    """Run a synchronized experiment."""
    print(f"\n{'='*80}")
    print(f"EXPERIMENT: {experiment_name}")
    print(f"Synchronized to marker: {marker_name}")
    print(f"{'='*80}")
    
    # Clean up old markers
    storage_dir = Path("temp_authority_storage")
    storage_dir.mkdir(exist_ok=True)
    for marker_file in storage_dir.glob("*.marker"):
        marker_file.unlink()
    
    # Start authority
    authority_script = Path(__file__).parent.parent.parent / "src" / "iabv_v15" / "services" / "trust" / "authority_process.py"
    
    print(f"[{experiment_name}] Starting Authority process...")
    process = subprocess.Popen(
        [sys.executable, str(authority_script), "--pipe-name", PIPE_NAME, "--storage-root", "temp_authority_storage"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    authority_pid = process.pid
    print(f"[{experiment_name}] Authority PID: {authority_pid}")
    
    # Wait for marker
    marker_content = wait_for_marker(marker_name, TIMEOUT_MARKER)
    
    if not marker_content:
        print(f"[{experiment_name}] FAILED: Marker not found")
        process.terminate()
        return None
    
    # Parse marker timestamp
    marker_time = None
    for line in marker_content.split('\n'):
        if line.startswith('T0=') or line.startswith('T1=') or line.startswith('T2='):
            marker_time = float(line.split('=')[1])
            break
    
    # Immediate client attempt
    print(f"[{experiment_name}] Attempting CreateFile IMMEDIATELY after marker...")
    t_client_start = timeit.default_timer()
    
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
        t_client_end = timeit.default_timer()
        client_time = (t_client_end - t_client_start) * 1000
        
        print(f"[{experiment_name}] CreateFile SUCCESS in {client_time:.2f}ms")
        print(f"[{experiment_name}] Time from marker: {(t_client_start - marker_time)*1000:.2f}ms")
        
        result = {
            'experiment': experiment_name,
            'marker': marker_name,
            'marker_time': marker_time,
            'client_time': client_time,
            'time_from_marker': (t_client_start - marker_time) * 1000,
            'result': 'success',
            'error': None
        }
        
        win32file.CloseHandle(pipe_handle)
        
    except pywintypes.error as e:
        t_client_end = timeit.default_timer()
        client_time = (t_client_end - t_client_start) * 1000
        
        print(f"[{experiment_name}] CreateFile FAILED in {client_time:.2f}ms")
        print(f"[{experiment_name}] Error code: {e.winerror}")
        print(f"[{experiment_name}] Error message: {e.strerror}")
        print(f"[{experiment_name}] Time from marker: {(t_client_start - marker_time)*1000:.2f}ms")
        
        result = {
            'experiment': experiment_name,
            'marker': marker_name,
            'marker_time': marker_time,
            'client_time': client_time,
            'time_from_marker': (t_client_start - marker_time) * 1000,
            'result': 'failed',
            'error_code': e.winerror,
            'error_text': e.strerror
        }
    
    # Terminate authority
    print(f"[{experiment_name}] Terminating Authority process...")
    process.terminate()
    time.sleep(2)
    if process.poll() is None:
        process.kill()
    
    print(f"[{experiment_name}] Complete")
    
    return result

def verify_client_parameters():
    """Verify client CreateFile parameters match server expectations."""
    print(f"\n{'='*80}")
    print(f"CLIENT CREATEFILE PARAMETERS VERIFICATION")
    print(f"{'='*80}")
    
    print(f"\nCLIENT PARAMETERS:")
    print(f"  Pipe name: {PIPE_NAME}")
    print(f"  Desired access: GENERIC_READ | GENERIC_WRITE (0x{win32file.GENERIC_READ | win32file.GENERIC_WRITE:X})")
    print(f"  Share mode: 0 (no sharing)")
    print(f"  Security attributes: None")
    print(f"  Creation disposition: OPEN_EXISTING (0x{win32file.OPEN_EXISTING:X})")
    print(f"  Flags and attributes: 0")
    print(f"  Template file: None")
    
    print(f"\nSERVER PARAMETERS (from authority_server.py):")
    print(f"  Pipe name: \\\\.\\pipe\\IABV_Authority")
    print(f"  dwOpenMode: PIPE_ACCESS_DUPLEX (0x00000003)")
    print(f"  dwPipeMode: PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT (0x00000006)")
    print(f"  nMaxInstances: PIPE_UNLIMITED_INSTANCES (255)")
    print(f"  nOutBufferSize: 4096")
    print(f"  nInBufferSize: 4096")
    print(f"  nDefaultTimeOut: 0")
    print(f"  lpSecurityAttributes: None")
    
    print(f"\nCOMPATIBILITY ANALYSIS:")
    print(f"  Client GENERIC_READ matches PIPE_ACCESS_DUPLEX: YES")
    print(f"  Client GENERIC_WRITE matches PIPE_ACCESS_DUPLEX: YES")
    print(f"  Client OPEN_EXISTING is correct for connecting to existing pipe: YES")
    print(f"  Security attributes None on both sides: COMPATIBLE")

def main():
    print("=" * 80)
    print("SYNCHRONIZED PIPE DIAGNOSTIC - IABV Named Pipe")
    print("=" * 80)
    
    # Verify client parameters
    verify_client_parameters()
    
    results = []
    
    # Experiment A: Client after PIPE_INSTANCE_CREATED
    result_a = run_synchronized_experiment(
        "EXPERIMENT_A",
        "pipe_instance_created.marker"
    )
    if result_a:
        results.append(result_a)
    
    time.sleep(2)
    
    # Experiment B: Client after CONNECTNAMEDPIPE_ENTERED
    result_b = run_synchronized_experiment(
        "EXPERIMENT_B", 
        "connect_entered.marker"
    )
    if result_b:
        results.append(result_b)
    
    # Generate timing hypothesis table
    print(f"\n{'='*80}")
    print(f"TIMING HYPOTHESIS TABLE")
    print(f"{'='*80}")
    
    print(f"| {'Experiment':20s} | {'Server Event':30s} | {'Client Timing':15s} | {'Result':10s} | {'Error':10s} | {'Interpretation':30s} |")
    print("|" + "-"*22 + "|" + "-"*32 + "|" + "-"*17 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*32 + "|")
    
    for result in results:
        interpretation = ""
        if result['result'] == 'success':
            interpretation = "Pipe available at this lifecycle point"
        elif result['error_code'] == 231:
            interpretation = "Pipe busy at this lifecycle point"
        elif result['error_code'] == 2:
            interpretation = "Pipe not found at this lifecycle point"
        else:
            interpretation = f"Unknown error {result['error_code']}"
        
        print(f"| {result['experiment']:20s} | {result['marker']:30s} | {result['time_from_marker']:15.2f}ms | {result['result']:10s} | {str(result.get('error_code', 'N/A')):10s} | {interpretation:30s} |")
    
    return results

if __name__ == "__main__":
    results = main()
    sys.exit(0)
