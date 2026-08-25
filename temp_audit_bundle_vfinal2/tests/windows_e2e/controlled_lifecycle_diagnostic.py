"""Controlled lifecycle diagnostic for IABV Named Pipe

This script uses multiprocessing synchronization to perform client connection
at exact points in the server lifecycle to determine the root cause of
ERROR_PIPE_BUSY.

NO PRODUCTION CHANGES - ONLY DIAGNOSTIC CAPTURE.
"""

import os
import sys
import time
import multiprocessing
import win32file
import win32pipe
import pywintypes
from pathlib import Path
import timeit
import threading

# Configuration
PIPE_NAME = r"\\.\pipe\IABV_Authority"

def server_process(pipe_created_event, connect_before_event, connect_entered_event, shutdown_event):
    """Server process that signals lifecycle events."""
    print(f"[SERVER] Starting server process PID={os.getpid()}")
    
    # Import after fork to avoid issues
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from iabv_v15.services.trust.authority_service import AuthorityService
    from iabv_v15.services.trust.authority_server import AuthorityServer
    import win32pipe
    import win32file
    
    storage_root = Path("temp_authority_storage")
    storage_root.mkdir(parents=True, exist_ok=True)
    
    # Initialize authority
    authority = AuthorityService(storage_root=storage_root)
    server = AuthorityServer(authority, pipe_name=PIPE_NAME)
    
    # Override server loop to signal events
    original_server_loop = server._server_loop
    
    def instrumented_server_loop():
        """Instrumented server loop with event signaling."""
        print(f"[SERVER] Server loop starting")
        pipe_count = 0
        
        while True:
            if shutdown_event.is_set():
                break
            
            try:
                pipe_count += 1
                print(f"[SERVER] Creating pipe #{pipe_count}")
                
                # Create named pipe
                pipe_handle = server._create_named_pipe()
                print(f"[SERVER] Pipe created: {pipe_handle}")
                
                # SIGNAL: Pipe created
                t0 = timeit.default_timer()
                print(f"[SERVER] SIGNALING: PIPE_CREATED at T0={t0:.6f}")
                pipe_created_event.set()
                
                # SIGNAL: Before ConnectNamedPipe
                t1 = timeit.default_timer()
                print(f"[SERVER] SIGNALING: CONNECT_BEFORE at T1={t1:.6f}")
                connect_before_event.set()
                
                # Small delay to allow client to act
                time.sleep(0.1)
                
                # SIGNAL: ConnectNamedPipe entered
                t2 = timeit.default_timer()
                print(f"[SERVER] SIGNALING: CONNECT_ENTERED at T2={t2:.6f}")
                connect_entered_event.set()
                
                # Call ConnectNamedPipe (blocking)
                print(f"[SERVER] Calling ConnectNamedPipe (blocking)")
                win32pipe.ConnectNamedPipe(pipe_handle)
                
                t3 = timeit.default_timer()
                print(f"[SERVER] CONNECT_EXITED at T3={t3:.6f}")
                
                # Handle client
                server._handle_client(pipe_handle)
                
                # Close pipe
                win32file.CloseHandle(pipe_handle)
                print(f"[SERVER] Pipe closed")
                
            except Exception as e:
                print(f"[SERVER] Error: {e}")
                import traceback
                traceback.print_exc()
                break
    
    # Start server in thread
    server_thread = threading.Thread(target=instrumented_server_loop)
    server_thread.daemon = True
    server_thread.start()
    
    # Keep server alive
    try:
        while not shutdown_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    
    print(f"[SERVER] Server process exiting")

def client_experiment(experiment_name, pipe_created_event, connect_before_event, connect_entered_event, wait_for_event):
    """Client experiment synchronized to specific server event."""
    print(f"\n[CLIENT] {experiment_name}")
    print(f"[CLIENT] Waiting for event: {wait_for_event}")
    
    # Wait for specified event
    if wait_for_event == "PIPE_CREATED":
        pipe_created_event.wait(timeout=10)
    elif wait_for_event == "CONNECT_BEFORE":
        connect_before_event.wait(timeout=10)
    elif wait_for_event == "CONNECT_ENTERED":
        connect_entered_event.wait(timeout=10)
    
    t_client_start = timeit.default_timer()
    print(f"[CLIENT] Attempting CreateFile at T={t_client_start:.6f}")
    
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
        
        print(f"[CLIENT] CreateFile SUCCESS in {client_time:.2f}ms")
        
        result = {
            'experiment': experiment_name,
            'wait_for_event': wait_for_event,
            'result': 'success',
            'client_time_ms': client_time,
            'error': None
        }
        
        win32file.CloseHandle(pipe_handle)
        
    except pywintypes.error as e:
        t_client_end = timeit.default_timer()
        client_time = (t_client_end - t_client_start) * 1000
        
        print(f"[CLIENT] CreateFile FAILED in {client_time:.2f}ms")
        print(f"[CLIENT] Error code: {e.winerror}")
        print(f"[CLIENT] Error message: {e.strerror}")
        
        result = {
            'experiment': experiment_name,
            'wait_for_event': wait_for_event,
            'result': 'failed',
            'client_time_ms': client_time,
            'error_code': e.winerror,
            'error_text': e.strerror
        }
    
    return result

def run_controlled_experiment(experiment_name, wait_for_event):
    """Run a controlled experiment with synchronization."""
    print(f"\n{'='*80}")
    print(f"CONTROLLED EXPERIMENT: {experiment_name}")
    print(f"Synchronized to: {wait_for_event}")
    print(f"{'='*80}")
    
    # Create synchronization events
    pipe_created_event = multiprocessing.Event()
    connect_before_event = multiprocessing.Event()
    connect_entered_event = multiprocessing.Event()
    shutdown_event = multiprocessing.Event()
    
    # Start server process
    server_p = multiprocessing.Process(
        target=server_process,
        args=(pipe_created_event, connect_before_event, connect_entered_event, shutdown_event)
    )
    server_p.start()
    print(f"[MAIN] Server process started PID={server_p.pid}")
    
    # Wait for server to initialize
    time.sleep(2)
    
    # Run client experiment
    result = client_experiment(experiment_name, pipe_created_event, connect_before_event, connect_entered_event, wait_for_event)
    
    # Shutdown server
    print(f"[MAIN] Shutting down server")
    shutdown_event.set()
    time.sleep(1)
    
    if server_p.is_alive():
        server_p.terminate()
        time.sleep(1)
        if server_p.is_alive():
            server_p.kill()
    
    server_p.join(timeout=5)
    print(f"[MAIN] Server process terminated")
    
    return result

def main():
    print("=" * 80)
    print("CONTROLLED LIFECYCLE DIAGNOSTIC - IABV Named Pipe")
    print("=" * 80)
    
    # Environment info
    print(f"\nENVIRONMENT:")
    print(f"  OS: Windows")
    print(f"  Python: {sys.version}")
    print(f"  Pipe name: {PIPE_NAME}")
    print(f"  User: {os.environ.get('USERNAME', 'unknown')}")
    
    results = []
    
    # Experiment A: Client after PIPE_CREATED (before ConnectNamedPipe)
    result_a = run_controlled_experiment("EXPERIMENT_A", "PIPE_CREATED")
    if result_a:
        results.append(result_a)
    
    time.sleep(2)
    
    # Experiment B: Client after CONNECT_ENTERED (while ConnectNamedPipe pending)
    result_b = run_controlled_experiment("EXPERIMENT_B", "CONNECT_ENTERED")
    if result_b:
        results.append(result_b)
    
    # Generate results table
    print(f"\n{'='*80}")
    print(f"CONTROLLED EXPERIMENT RESULTS")
    print(f"{'='*80}")
    
    print(f"| {'Experiment':20s} | {'Synchronization':25s} | {'Result':10s} | {'Error':10s} | {'Interpretation':30s} |")
    print("|" + "-"*22 + "|" + "-"*27 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*32 + "|")
    
    for result in results:
        interpretation = ""
        if result['result'] == 'success':
            interpretation = "Client can connect at this lifecycle point"
        elif result['error_code'] == 231:
            interpretation = "Pipe busy at this lifecycle point"
        elif result['error_code'] == 2:
            interpretation = "Pipe not found at this lifecycle point"
        else:
            interpretation = f"Unknown error {result['error_code']}"
        
        print(f"| {result['experiment']:20s} | {result['wait_for_event']:25s} | {result['result']:10s} | {str(result.get('error_code', 'N/A')):10s} | {interpretation:30s} |")
    
    return results

if __name__ == "__main__":
    if __name__ == "__main__":
        multiprocessing.freeze_support()
        results = main()
        sys.exit(0)
