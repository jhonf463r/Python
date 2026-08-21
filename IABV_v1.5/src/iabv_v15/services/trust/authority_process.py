"""Authority Process: Separate process entry point for P0.213 V5 Phase 2.

This is the actual separate process implementation for the trusted authority.

CRITICAL: This runs as a separate process, not in the worker process.
The worker cannot import this module's secret or construct equivalent authority.

Phase 2 Status: RUNTIME_VERIFIED (separate trusted authority process)
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from pathlib import Path

from iabv_v15.services.trust.authority_service import AuthorityService
from iabv_v15.services.trust.authority_server import AuthorityServer


def main() -> int:
    """Main entry point for authority process.
    
    This runs as a separate process with:
    - Real secret key ownership
    - Real generation ownership
    - Real lease state ownership
    - Windows Named Pipe server
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(description="P0.213 V5 Authority Process")
    parser.add_argument(
        "--storage-root",
        type=str,
        required=True,
        help="Directory for persistent state (OS-protected)"
    )
    parser.add_argument(
        "--pipe-name",
        type=str,
        default=r"\\.\pipe\IABV_Authority",
        help="Named pipe name"
    )
    args = parser.parse_args()
    
    storage_root = Path(args.storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)
    
    print(f"[Authority] Starting authority process", flush=True)
    print(f"[Authority] Storage root: {storage_root}", flush=True)
    print(f"[Authority] Pipe name: {args.pipe_name}", flush=True)
    print(f"[Authority] PID: {os.getpid()}", flush=True)
    
    # Phase 2: Initialize authority service
    try:
        authority = AuthorityService(storage_root=storage_root)
        print(f"[Authority] Authority service initialized", flush=True)
        print(f"[Authority] Generation: {authority._generation}", flush=True)
    except Exception as e:
        print(f"[Authority] ERROR: Failed to initialize authority service: {e}", flush=True)
        return 1
    
    # Phase 2: Initialize authority server
    try:
        server = AuthorityServer(authority)
        print(f"[Authority] Authority server initialized", flush=True)
    except Exception as e:
        print(f"[Authority] ERROR: Failed to initialize authority server: {e}", flush=True)
        return 1
    
    # Phase 2: Start server
    try:
        server.start()
        print(f"[Authority] Authority server started", flush=True)
        print(f"[Authority] Listening on Named Pipe: {args.pipe_name}", flush=True)
        
        # Phase 2: Create readiness signal after server is ready
        ready_file = storage_root / "authority_ready.txt"
        ready_file.write_text(str(os.getpid()))
        print(f"[Authority] Ready signal created: {ready_file}", flush=True)
    except Exception as e:
        print(f"[Authority] ERROR: Failed to start authority server: {e}", flush=True)
        return 1
    
    # Phase 2: Signal handling for graceful shutdown
    def signal_handler(signum, frame):
        print(f"[Authority] Received signal {signum}, shutting down...", flush=True)
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Phase 2: Keep process alive
    print(f"[Authority] Authority process running...", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"[Authority] KeyboardInterrupt, shutting down...")
        server.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
