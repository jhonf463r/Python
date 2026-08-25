"""High-resolution timestamp diagnostic for IABV Named Pipe

This script performs detailed timing experiments to determine the exact
lifecycle behavior of the Named Pipe instance.

NO CODE CHANGES - ONLY DIAGNOSTIC CAPTURE.
"""

import os
import sys
import time
import subprocess
import threading
import win32file
import win32pipe
import win32api
import win32security
import pywintypes
from pathlib import Path
from datetime import datetime
import timeit

# Configuration
PIPE_NAME = r"\\.\pipe\IABV_Authority"
TIMEOUT_AUTHORITY_START = 15
TIMEOUT_PIPE_CREATION = 15

class EventLogger:
    """High-resolution event logger."""
    
    def __init__(self):
        self.events = []
        self.lock = threading.Lock()
    
    def log(self, event, pid=None, thread_id=None, pipe_handle=None, state=None, result=None, error=None):
        """Log an event with high-resolution timestamp."""
        with self.lock:
            timestamp = timeit.default_timer()  # High-resolution timer
            self.events.append({
                'event': event,
                'timestamp': timestamp,
                'datetime': datetime.now().isoformat(),
                'pid': pid or os.getpid(),
                'thread_id': thread_id or threading.get_ident(),
                'pipe_handle': str(pipe_handle) if pipe_handle else None,
                'state': state,
                'result': result,
                'error': str(error) if error else None
            })
    
    def get_table(self):
        """Generate event table."""
        return self.events

logger = EventLogger()

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
        if e.winerror == 2:
            return False
        elif e.winerror == 231:
            return True
        else:
            return False

def run_timing_experiment(delay_ms, experiment_name, logger):
    """Run a timing experiment with specified delay."""
    print(f"\n{'='*80}")
    print(f"EXPERIMENT: {experiment_name}")
    print(f"Delay: {delay_ms}ms")
    print(f"{'='*80}")
    
    # Start authority
    authority_script = Path(__file__).parent.parent.parent / "src" / "iabv_v15" / "services" / "trust" / "authority_process.py"
    
    logger.log(f"{experiment_name}_START_AUTHORITY")
    process = subprocess.Popen(
        [sys.executable, str(authority_script), "--pipe-name", PIPE_NAME, "--storage-root", "temp_authority_storage"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    authority_pid = process.pid
    logger.log(f"{experiment_name}_AUTHORITY_PID", pid=authority_pid, result=authority_pid)
    print(f"[{experiment_name}] Authority PID: {authority_pid}")
    
    time.sleep(2)
    
    # Wait for pipe creation
    pipe_created = False
    for i in range(TIMEOUT_PIPE_CREATION):
        if check_pipe_exists(PIPE_NAME):
            pipe_created = True
            logger.log(f"{experiment_name}_PIPE_CREATED", result="success")
            print(f"[{experiment_name}] Pipe created after {i}s")
            break
        time.sleep(1)
    
    if not pipe_created:
        logger.log(f"{experiment_name}_PIPE_CREATION_FAILED", result="failed")
        process.terminate()
        return None
    
    # Apply delay
    if delay_ms > 0:
        print(f"[{experiment_name}] Waiting {delay_ms}ms before CreateFile...")
        time.sleep(delay_ms / 1000.0)
        logger.log(f"{experiment_name}_DELAY_APPLIED", result=f"{delay_ms}ms")
    
    # Attempt CreateFile
    logger.log(f"{experiment_name}_CREATEFILE_START")
    print(f"[{experiment_name}] Attempting CreateFile...")
    
    t3 = timeit.default_timer()
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
        t4 = timeit.default_timer()
        logger.log(f"{experiment_name}_CREATEFILE_SUCCESS", pipe_handle=pipe_handle, result="success")
        print(f"[{experiment_name}] CreateFile succeeded in {(t4-t3)*1000:.2f}ms")
        win32file.CloseHandle(pipe_handle)
        
    except pywintypes.error as e:
        t4 = timeit.default_timer()
        logger.log(f"{experiment_name}_CREATEFILE_FAILED", error=e, result=f"error_{e.winerror}")
        print(f"[{experiment_name}] CreateFile failed after {(t4-t3)*1000:.2f}ms")
        print(f"[{experiment_name}] Error code: {e.winerror}")
        
        # Immediate WaitNamedPipe
        logger.log(f"{experiment_name}_WAITNAMEDPIPE_START")
        print(f"[{experiment_name}] Attempting WaitNamedPipe immediately...")
        
        t5 = timeit.default_timer()
        try:
            result = win32pipe.WaitNamedPipe(PIPE_NAME, 1000)  # 1 second
            t6 = timeit.default_timer()
            logger.log(f"{experiment_name}_WAITNAMEDPIPE_RESULT", result=str(result))
            print(f"[{experiment_name}] WaitNamedPipe returned: {result} in {(t6-t5)*1000:.2f}ms")
        except pywintypes.error as e2:
            t6 = timeit.default_timer()
            logger.log(f"{experiment_name}_WAITNAMEDPIPE_FAILED", error=e2)
            print(f"[{experiment_name}] WaitNamedPipe failed: {e2.winerror} in {(t6-t5)*1000:.2f}ms")
    
    # Check server state
    if process.poll() is None:
        logger.log(f"{experiment_name}_SERVER_ALIVE", result="true")
    else:
        logger.log(f"{experiment_name}_SERVER_DEAD", result=str(process.returncode))
    
    # Terminate
    process.terminate()
    time.sleep(2)
    if process.poll() is None:
        process.kill()
    
    logger.log(f"{experiment_name}_COMPLETE")
    print(f"[{experiment_name}] Complete")
    
    return logger.get_table()

def run_dual_client_experiment(logger):
    """Run experiment with two independent clients."""
    print(f"\n{'='*80}")
    print(f"EXPERIMENT: DUAL_CLIENT")
    print(f"{'='*80}")
    
    # Start authority
    authority_script = Path(__file__).parent.parent.parent / "src" / "iabv_v15" / "services" / "trust" / "authority_process.py"
    
    logger.log("DUAL_CLIENT_START_AUTHORITY")
    process = subprocess.Popen(
        [sys.executable, str(authority_script), "--pipe-name", PIPE_NAME, "--storage-root", "temp_authority_storage"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    authority_pid = process.pid
    logger.log("DUAL_CLIENT_AUTHORITY_PID", pid=authority_pid, result=authority_pid)
    print(f"[DUAL_CLIENT] Authority PID: {authority_pid}")
    
    time.sleep(2)
    
    # Wait for pipe creation
    pipe_created = False
    for i in range(TIMEOUT_PIPE_CREATION):
        if check_pipe_exists(PIPE_NAME):
            pipe_created = True
            logger.log("DUAL_CLIENT_PIPE_CREATED", result="success")
            print(f"[DUAL_CLIENT] Pipe created after {i}s")
            break
        time.sleep(1)
    
    if not pipe_created:
        logger.log("DUAL_CLIENT_PIPE_CREATION_FAILED", result="failed")
        process.terminate()
        return None
    
    # Launch two clients simultaneously
    def client_attempt(client_id, logger):
        logger.log(f"DUAL_CLIENT_{client_id}_START")
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
            logger.log(f"DUAL_CLIENT_{client_id}_SUCCESS", pipe_handle=pipe_handle, result="success")
            print(f"[DUAL_CLIENT] Client {client_id} succeeded")
            win32file.CloseHandle(pipe_handle)
        except pywintypes.error as e:
            logger.log(f"DUAL_CLIENT_{client_id}_FAILED", error=e, result=f"error_{e.winerror}")
            print(f"[DUAL_CLIENT] Client {client_id} failed: {e.winerror}")
    
    logger.log("DUAL_CLIENT_BOTH_START")
    print(f"[DUAL_CLIENT] Launching both clients simultaneously...")
    
    thread1 = threading.Thread(target=client_attempt, args=("A", logger))
    thread2 = threading.Thread(target=client_attempt, args=("B", logger))
    
    t_start = timeit.default_timer()
    thread1.start()
    thread2.start()
    
    thread1.join()
    thread2.join()
    t_end = timeit.default_timer()
    
    logger.log("DUAL_CLIENT_BOTH_COMPLETE", result=f"{(t_end-t_start)*1000:.2f}ms")
    print(f"[DUAL_CLIENT] Both clients completed in {(t_end-t_start)*1000:.2f}ms")
    
    # Terminate
    process.terminate()
    time.sleep(2)
    if process.poll() is None:
        process.kill()
    
    logger.log("DUAL_CLIENT_COMPLETE")
    return logger.get_table()

def main():
    print("=" * 80)
    print("HIGH-RESOLUTION TIMESTAMP DIAGNOSTIC - IABV Named Pipe")
    print("=" * 80)
    
    all_events = []
    
    # Experiment A: Immediate
    events_a = run_timing_experiment(0, "EXPERIMENT_A", logger)
    if events_a:
        all_events.extend(events_a)
    
    time.sleep(2)
    
    # Experiment B: 100ms
    events_b = run_timing_experiment(100, "EXPERIMENT_B", logger)
    if events_b:
        all_events.extend(events_b)
    
    time.sleep(2)
    
    # Experiment C: 1000ms
    events_c = run_timing_experiment(1000, "EXPERIMENT_C", logger)
    if events_c:
        all_events.extend(events_c)
    
    time.sleep(2)
    
    # Dual client experiment
    events_dual = run_dual_client_experiment(logger)
    if events_dual:
        all_events.extend(events_dual)
    
    # Generate event table
    print("\n" + "=" * 80)
    print("REQUIRED EVENT TABLE")
    print("=" * 80)
    
    # Calculate relative timestamps
    if all_events:
        base_time = all_events[0]['timestamp']
        
        print(f"| {'Event':40s} | {'Timestamp (ms)':15s} | {'PID':8s} | {'Thread':8s} | {'State':15s} | {'Result':15s} | {'Error':15s} |")
        print("|" + "-"*40 + "|" + "-"*17 + "|" + "-"*10 + "|" + "-"*10 + "|" + "-"*17 + "|" + "-"*17 + "|" + "-"*17 + "|")
        
        for event in all_events:
            rel_time = (event['timestamp'] - base_time) * 1000
            print(f"| {event['event']:40s} | {rel_time:15.2f} | {event['pid']:8d} | {event['thread_id']:8d} | {str(event['state'])[:15]:15s} | {str(event['result'])[:15]:15s} | {str(event['error'])[:15]:15s} |")
    
    return all_events

if __name__ == "__main__":
    events = main()
    sys.exit(0)
